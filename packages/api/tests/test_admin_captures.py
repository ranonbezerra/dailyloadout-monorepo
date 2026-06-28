"""Backoffice (Epic 21) Phase 6: captures moderation.

Covers `/internal/v1/captures` — cross-user list/search with per-status tallies,
detail with the candidate review queue, reprocess (re-runs the inline pipeline
for text captures), and purge. Admin-gated and audited like the rest of the
backoffice.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select

from dailyloadout.infrastructure.db.models import (
    AdminAuditLog,
    Capture,
    CaptureCandidate,
    User,
)
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Cap Admin",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "capadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_capture(
    *,
    email: str,
    status: str = "review",
    input_type: str = "text",
    raw_text: str | None = "I played Halo last night",
    error_message: str | None = None,
    candidate_titles: list[str] | None = None,
) -> str:
    """Create an owner + a capture (with optional candidates); return its public_id."""
    async with _TestSessionFactory() as session:
        user = User(
            email=email,
            password_hash="x",  # pragma: allowlist secret
            display_name="Owner",
        )
        session.add(user)
        await session.flush()
        capture = Capture(
            user_id=user.id,
            input_type=input_type,
            raw_text=raw_text,
            status=status,
            error_message=error_message,
        )
        session.add(capture)
        await session.flush()
        pid = str(capture.public_id)
        for title in candidate_titles or []:
            session.add(CaptureCandidate(capture_id=capture.id, title=title, status="pending"))
        await session.commit()
        return pid


class TestCapturesAuthz:
    async def test_list_requires_admin(self, async_client: AsyncClient) -> None:
        assert (await async_client.get("/internal/v1/captures")).status_code == 401
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.get("/internal/v1/captures", headers=headers)
        assert resp.status_code == 403


class TestCapturesList:
    async def test_lists_with_counts_and_tallies(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_capture(email="a@example.com", status="review", candidate_titles=["X", "Y"])
        await _make_capture(email="b@example.com", status="failed", raw_text="bad")

        resp = await async_client.get("/internal/v1/captures", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        tallies = {row["status"]: row["count"] for row in body["status_counts"]}
        assert tallies == {"review": 1, "failed": 1}
        by_email = {c["user_email"]: c for c in body["items"]}
        assert by_email["a@example.com"]["candidate_count"] == 2
        assert by_email["b@example.com"]["status"] == "failed"

    async def test_filters_by_status(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_capture(email="a@example.com", status="review")
        await _make_capture(email="b@example.com", status="failed")
        resp = await async_client.get("/internal/v1/captures?status=failed", headers=headers)
        items = resp.json()["items"]
        assert [c["user_email"] for c in items] == ["b@example.com"]

    async def test_search_matches_owner_email(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_capture(email="alice@example.com", status="review")
        await _make_capture(email="bob@example.com", status="review")
        resp = await async_client.get("/internal/v1/captures?q=alice", headers=headers)
        items = resp.json()["items"]
        assert [c["user_email"] for c in items] == ["alice@example.com"]


class TestCapturesModeration:
    async def test_detail_and_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_capture(
            email="a@example.com", status="failed", candidate_titles=["Stale Game"]
        )
        resp = await async_client.get(f"/internal/v1/captures/{pid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_email"] == "a@example.com"
        assert body["reprocessable"] is True
        assert [c["title"] for c in body["candidates"]] == ["Stale Game"]

        missing = await async_client.get(
            "/internal/v1/captures/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert missing.status_code == 404

    async def test_reprocess_reruns_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_capture(
            email="a@example.com",
            status="failed",
            raw_text="I played Halo last night",
            error_message="Processing failed. Please try again.",
            candidate_titles=["STALE GAME"],
        )
        resp = await async_client.post(f"/internal/v1/captures/{pid}/reprocess", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # The dummy LLM extracts at least one title → capture lands in review.
        assert body["status"] == "review"
        titles = {c["title"] for c in body["candidates"]}
        assert "STALE GAME" not in titles  # old candidates cleared
        assert len(titles) >= 1
        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None and row.action == "capture.reprocess"

    async def test_reprocess_rejects_sourceless_capture(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_capture(
            email="a@example.com", status="failed", input_type="photo", raw_text=None
        )
        resp = await async_client.post(f"/internal/v1/captures/{pid}/reprocess", headers=headers)
        assert resp.status_code == 422

    async def test_purge_deletes_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_capture(
            email="a@example.com", status="failed", candidate_titles=["Junk"]
        )
        resp = await async_client.delete(f"/internal/v1/captures/{pid}", headers=headers)
        assert resp.status_code == 204
        async with _TestSessionFactory() as session:
            remaining = (
                await session.execute(select(func.count()).select_from(Capture))
            ).scalar_one()
            assert remaining == 0
            audited = (
                await session.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(AdminAuditLog.action == "capture.purge")
                )
            ).scalar_one()
            assert audited == 1

    async def test_purge_404_for_unknown(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.delete(
            "/internal/v1/captures/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert resp.status_code == 404
