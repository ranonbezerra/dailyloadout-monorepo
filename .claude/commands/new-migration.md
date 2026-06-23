# /new-migration

Create a new Alembic migration for the DailyLoadout API.

## Usage
```
/new-migration <description>
```

Example: `/new-migration add_playtime_to_missions`

## Steps

### 1. Verify models are up to date
- Confirm the SQLAlchemy model in `infrastructure/db/models/` reflects the desired change
- Confirm `alembic/env.py` imports all models (via `models/__init__.py`)

### 2. Generate the migration
```bash
cd packages/api && poetry run alembic revision --autogenerate -m "$ARGUMENTS"
```

### 3. Review the generated file
- Open the file in `alembic/versions/` just created
- Verify `upgrade()` and `downgrade()` do what's expected
- Add indexes manually if needed (autogenerate doesn't detect all)
- Verify `down_revision` points to the correct migration

### 4. Apply locally
```bash
cd packages/api && poetry run alembic upgrade head
```

### 5. Verify
```bash
cd packages/api && poetry run alembic current
```

## Naming conventions
- `create_{table}s_table` — new table
- `add_{column}_to_{table}s` — new column
- `add_idx_{table}s_{column}` — new index
- `alter_{table}s_{change}` — modify existing

## Schema conventions
- **UUID v4 as public_id**: `public_id VARCHAR UNIQUE NOT NULL DEFAULT gen_random_uuid()`
- **Timestamps UTC**: `TIMESTAMPTZ DEFAULT now()`
- **Indexes for FKs**: always create index for foreign key columns
- **ENUMs**: create via `sa.Enum()` in SQLAlchemy, not raw SQL strings

## When to use manual migration (no autogenerate)
- Seed data
- Enum value changes
- Custom indexes (partial, expression, GIN trigram)
- Rename columns/tables (autogenerate creates drop+create)
- PostgreSQL extensions (`pg_trgm`, `unaccent`, `citext`)
