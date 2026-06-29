-- Slate — PostgreSQL extensions bootstrap
-- Runs once on first container start (docker-entrypoint-initdb.d)

CREATE EXTENSION IF NOT EXISTS citext;       -- case-insensitive emails
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- trigram fuzzy search on titles
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()
