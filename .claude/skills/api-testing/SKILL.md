---
name: api-testing
description: Load when writing unit tests, integration tests, fixing test failures, or improving test coverage for the DailyLoadout API.
---

# API Testing — DailyLoadout

## Commands

```bash
cd packages/api
poetry run pytest                                            # all tests
poetry run pytest -v                                         # verbose
poetry run pytest tests/test_mission.py                      # specific file
poetry run pytest -k "test_create_mission"                   # name pattern
poetry run pytest --cov=src/dailyloadout --cov-report=term-missing  # coverage
poetry run pytest -x                                         # stop on first failure
poetry run pytest --tb=short                                 # short traceback
```

Or via Makefile:
```bash
make api-test                # all tests
make api-test-cov            # tests + coverage >= 90%
```

## Coverage Targets

| Module | Target |
|--------|--------|
| Overall | >= 90% |
| Core services | >= 90% |
| Repositories | >= 85% |
| API routes | >= 80% |
| LLM integration | >= 75% |

## Directory Structure

```
tests/
├── conftest.py                  # Shared fixtures (db, client, auth, factories)
├── test_auth.py                 # Authentication tests
├── test_capture.py              # Capture flow tests
├── test_library.py              # Library CRUD tests
├── test_loadout.py              # Loadout suggestion tests
├── test_mission.py              # Mission lifecycle tests
├── test_stats.py                # Analytics tests
└── test_debrief_task.py         # Async task tests
```

## Test Fixtures (conftest.py)

The test suite uses an in-memory PostgreSQL test database. Key fixtures:

```python
@pytest.fixture
async def async_client(app):
    """HTTP client for integration tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(async_client):
    """Register + login, return auth headers."""
    # Returns {"Authorization": "Bearer <token>"}

@pytest.fixture
async def library_entry(async_client, auth_headers):
    """Create a library entry for testing."""
    # Returns the created entry dict
```

## Integration Test Pattern

```python
@pytest.mark.anyio
async def test_create_mission(async_client, auth_headers, library_entry):
    response = await async_client.post(
        "/api/v1/missions/",
        json={"library_entry_id": str(library_entry["public_id"])},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "public_id" in data
    assert data["status"] == "active"
    assert data["briefing_text"] is not None
```

## Testing LLM Integration

The test suite uses `LLM_PROVIDER=dummy` which returns canned responses:

```python
# The DummyLLMClient returns predefined responses
# Tests validate the flow (prompt -> parse -> validate -> persist)
# without hitting a real LLM

@pytest.mark.anyio
async def test_briefing_generation(async_client, auth_headers, library_entry):
    response = await async_client.post(
        "/api/v1/missions/",
        json={"library_entry_id": str(library_entry["public_id"])},
        headers=auth_headers,
    )
    assert response.status_code == 201
    # Dummy LLM returns a valid briefing
    assert response.json()["briefing_text"] is not None
```

## Testing Async Tasks (Taskiq)

```python
from dailyloadout.infrastructure.tasks.debrief_extraction import extract_debrief_state_task

@pytest.mark.anyio
async def test_debrief_extraction_task():
    # Call the original function directly (bypass broker)
    await extract_debrief_state_task.original_func(mission_public_id="...")
    # Verify the extraction was persisted
```

## Anti-Hallucination Test Pattern

```python
@pytest.mark.anyio
async def test_llm_output_validated_against_library(async_client, auth_headers):
    """LLM may hallucinate game names not in the user's library."""
    # Create specific library entries
    # Trigger LLM flow
    # Verify only known games appear in result
```

## Common Assertions

```python
# Entity has public_id
assert "public_id" in data

# Status transitions
assert data["status"] == "active"
assert data["status"] == "ended"

# Timestamps present
assert "created_at" in data
assert "updated_at" in data

# User isolation
response = await async_client.get(
    f"/api/v1/missions/{other_user_mission_id}",
    headers=auth_headers,
)
assert response.status_code == 404  # Cannot see other user's data

# One active mission constraint
response = await async_client.post(
    "/api/v1/missions/",
    json={"library_entry_id": str(entry["public_id"])},
    headers=auth_headers,
)
assert response.status_code == 409  # Already has active mission
```

## Test Data Helpers

Tests use helper functions from `conftest.py` or inline factories:

```python
async def _create_library_entry(client, headers, **overrides):
    """Create a library entry with sensible defaults."""
    payload = {
        "game_title": "Elden Ring",
        "genres": ["RPG", "Action"],
        "status": "playing",
        **overrides,
    }
    response = await client.post("/api/v1/library/", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()
```
