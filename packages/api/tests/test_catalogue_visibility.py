"""Repository-level tests for catalogue visibility + distinct-owner counting.

Exercises the ``GameRepository`` visibility rule and ``LibraryRepository``
distinct-owner count directly, complementing the HTTP-level tests in
``test_game_create.py``. The visibility rule is::

    igdb_id IS NOT NULL OR is_shared IS TRUE OR created_by_user_id = U
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import Platform, User
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from tests.conftest import _TestSessionFactory


async def _make_user(session: AsyncSession, email: str) -> int:
    user = User(email=email, password_hash="x", display_name="P")
    session.add(user)
    await session.flush()
    return user.id


class TestVisibilityRule:
    async def test_manual_row_defaults_private(self) -> None:
        async with _TestSessionFactory() as session:
            uid = await _make_user(session, "creator@example.com")
            repo = GameRepository(session)
            game = await repo.create(
                slug="private-one",
                title="Private One",
                metadata_source="manual",
                created_by_user_id=uid,
            )
            assert game.is_shared is False
            await session.commit()

    async def test_search_visible_to_creator_only_when_private(self) -> None:
        async with _TestSessionFactory() as session:
            creator = await _make_user(session, "a@example.com")
            other = await _make_user(session, "b@example.com")
            repo = GameRepository(session)
            await repo.create(
                slug="secret-game",
                title="Secret Game",
                metadata_source="manual",
                created_by_user_id=creator,
            )
            await session.commit()

            mine = await repo.search("Secret", user_id=creator)
            assert [g.slug for g in mine] == ["secret-game"]

            theirs = await repo.search("Secret", user_id=other)
            assert theirs == []

    async def test_shared_and_igdb_rows_visible_to_all(self) -> None:
        async with _TestSessionFactory() as session:
            creator = await _make_user(session, "a@example.com")
            other = await _make_user(session, "b@example.com")
            repo = GameRepository(session)
            # A legacy/promoted manual row explicitly marked shared (mirrors the
            # migration back-fill of pre-existing rows to is_shared=true).
            await repo.create(
                slug="promoted-game",
                title="Promoted Game",
                metadata_source="manual",
                created_by_user_id=creator,
                is_shared=True,
            )
            # A canonical IGDB row (visible via igdb_id, no creator).
            await repo.create(
                slug="canon-game",
                title="Canon Game",
                metadata_source="igdb",
                igdb_id=42,
            )
            await session.commit()

            found = {g.slug for g in await repo.search("Game", user_id=other)}
            assert {"promoted-game", "canon-game"} <= found

    async def test_distinct_genres_excludes_other_private_rows(self) -> None:
        async with _TestSessionFactory() as session:
            creator = await _make_user(session, "a@example.com")
            other = await _make_user(session, "b@example.com")
            repo = GameRepository(session)
            await repo.create(
                slug="g-private",
                title="G Private",
                metadata_source="manual",
                created_by_user_id=creator,
                genres=["private-genre"],
            )
            await repo.create(
                slug="g-shared",
                title="G Shared",
                metadata_source="igdb",
                igdb_id=99,
                genres=["public-genre"],
            )
            await session.commit()

            other_genres = await repo.distinct_genres(user_id=other)
            assert "public-genre" in other_genres
            assert "private-genre" not in other_genres

            creator_genres = await repo.distinct_genres(user_id=creator)
            assert "private-genre" in creator_genres


class TestCountDistinctOwners:
    async def test_counts_distinct_users_not_entries(self) -> None:
        async with _TestSessionFactory() as session:
            creator = await _make_user(session, "a@example.com")
            owner2 = await _make_user(session, "b@example.com")
            game_repo = GameRepository(session)
            lib_repo = LibraryRepository(session)
            game = await game_repo.create(
                slug="owned-game",
                title="Owned Game",
                metadata_source="manual",
                created_by_user_id=creator,
            )
            pc = Platform(slug="pc", label="PC", family="pc")
            ps5 = Platform(slug="ps5", label="PS5", family="playstation")
            session.add_all([pc, ps5])
            await session.flush()

            # creator on two platforms = still ONE distinct owner
            await lib_repo.create(user_id=creator, game_id=game.id, platform_id=pc.id)
            await lib_repo.create(user_id=creator, game_id=game.id, platform_id=ps5.id)
            assert await lib_repo.count_distinct_owners(game.id) == 1

            # a second distinct owner bumps the count
            await lib_repo.create(user_id=owner2, game_id=game.id, platform_id=pc.id)
            assert await lib_repo.count_distinct_owners(game.id) == 2
            await session.commit()


class TestPromotionThreshold:
    async def test_service_promotes_at_threshold(self) -> None:
        """``maybe_promote_to_shared`` flips is_shared once owners hit threshold."""
        from dailyloadout.core.library.promotion import maybe_promote_to_shared

        async with _TestSessionFactory() as session:
            creator = await _make_user(session, "a@example.com")
            owner2 = await _make_user(session, "b@example.com")
            game_repo = GameRepository(session)
            lib_repo = LibraryRepository(session)
            game = await game_repo.create(
                slug="threshold-game",
                title="Threshold Game",
                metadata_source="manual",
                created_by_user_id=creator,
            )
            pc = Platform(slug="pc", label="PC", family="pc")
            session.add(pc)
            await session.flush()

            kwargs = {
                "game_repo": game_repo,
                "library_repo": lib_repo,
                "igdb_client": None,
                "min_score": 0.6,
                "threshold": 2,
            }
            await lib_repo.create(user_id=creator, game_id=game.id, platform_id=pc.id)
            await maybe_promote_to_shared(game, creator, **kwargs)
            assert game.is_shared is False  # only one owner

            await lib_repo.create(user_id=owner2, game_id=game.id, platform_id=pc.id)
            await maybe_promote_to_shared(game, owner2, **kwargs)
            assert game.is_shared is True  # threshold reached
            await session.commit()

    async def test_igdb_row_not_repromoted(self) -> None:
        """Canonical/IGDB rows are already shared; promotion is a no-op."""
        from dailyloadout.core.library.promotion import maybe_promote_to_shared

        async with _TestSessionFactory() as session:
            game_repo = GameRepository(session)
            lib_repo = LibraryRepository(session)
            game = await game_repo.create(
                slug="igdb-game",
                title="IGDB Game",
                metadata_source="igdb",
                igdb_id=7,
                is_shared=True,
            )
            # No owners at all — must not error, must remain shared.
            await maybe_promote_to_shared(
                game,
                1,
                game_repo=game_repo,
                library_repo=lib_repo,
                igdb_client=None,
                min_score=0.6,
                threshold=1,
            )
            assert game.is_shared is True
            await session.commit()


async def test_search_excludes_other_users_private_after_threshold_not_met() -> None:
    """Sanity: below threshold the row remains hidden from non-creators."""
    async with _TestSessionFactory() as session:
        creator = await _make_user(session, "a@example.com")
        other = await _make_user(session, "b@example.com")
        repo = GameRepository(session)
        await repo.create(
            slug="still-private",
            title="Still Private",
            metadata_source="manual",
            created_by_user_id=creator,
        )
        await session.commit()
        assert await repo.search("Still", user_id=other) == []
