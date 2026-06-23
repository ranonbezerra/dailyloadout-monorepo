# /new-domain

Create the full structure for a new domain in the DailyLoadout API: router + service + schemas + repository + model + deps + tests.

## Usage
```
/new-domain <domain-name>
```

Example: `/new-domain achievement`

## What will be created

```
packages/api/
├── src/dailyloadout/
│   ├── api/v1/{domain}.py                       <- APIRouter with basic endpoints
│   ├── core/{domain}/
│   │   ├── service.py                            <- Service with business logic
│   │   └── schemas.py                            <- Pydantic v2 schemas
│   ├── deps/{domain}.py                          <- FastAPI Depends() provider
│   └── infrastructure/db/
│       ├── models/{domain}.py                    <- SQLAlchemy 2.x model
│       └── repositories/{domain}.py              <- Repository with DB access
└── tests/
    └── test_{domain}.py                          <- pytest tests
```

## Steps

### 1. Analyze the domain
- Read `ARCHITECTURE.md` and `PRODUCT.md` to understand the domain
- Identify the CRUD operations and business rules
- Check existing domains in `core/` for patterns to follow (e.g., `core/library/`, `core/mission/`)

### 2. Create the files
Follow established patterns strictly:
- **Model**: SQLAlchemy 2.x with `public_id` UUID, `created_at`/`updated_at` timestamps
- **Repository**: SQLAlchemy async, no business logic
- **Schemas**: Pydantic v2 with `model_config = ConfigDict(from_attributes=True)`
- **Service**: all business logic, calls repository only
- **Deps**: FastAPI `Depends()` wiring
- **Router**: parse/validate + call service, NO business logic

### 3. Register the router
Add to `main.py`:
```python
from dailyloadout.api.v1.{domain} import router as {domain}_router
app.include_router({domain}_router, prefix="/api/v1/{domain}s", tags=["{Domain}"])
```

### 4. Register the model
Add the import to `infrastructure/db/models/__init__.py` so Alembic sees it.

### 5. Create migration
```bash
cd packages/api && poetry run alembic revision --autogenerate -m "create_{domain}s_table"
```

### 6. Verify
```bash
cd packages/api && poetry run pytest tests/test_{domain}.py -v
cd packages/api && poetry run ruff check src/dailyloadout/api/v1/{domain}.py src/dailyloadout/core/{domain}/
cd packages/api && poetry run mypy src/dailyloadout/core/{domain}/
```

## Model Template

```python
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from dailyloadout.infrastructure.db.models.base import Base, TimestampMixin, PublicIDMixin

class {Domain}(Base, TimestampMixin, PublicIDMixin):
    __tablename__ = "{domain}s"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Add domain-specific columns

    user: Mapped["User"] = relationship(back_populates="{domain}s")
```

## Repository Template

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dailyloadout.infrastructure.db.models.{domain} import {Domain}

class {Domain}Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_public_id(self, public_id: str) -> {Domain} | None:
        stmt = select({Domain}).where({Domain}.public_id == public_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> {Domain}:
        entity = {Domain}(**kwargs)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
```
