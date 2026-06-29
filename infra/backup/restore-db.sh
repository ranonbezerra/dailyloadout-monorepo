#!/usr/bin/env bash
#
# Slate — restore a gzipped pg_dump into the running Postgres container.
#
# A backup you've never restored is not a backup. Test this against a scratch DB
# periodically. Usage:
#   ./restore-db.sh /var/backups/slate/slate-slate-20260627T033000Z.sql.gz
#
# Config via environment (same as backup-db.sh):
#   PG_CONTAINER (default slate-postgres), POSTGRES_USER, POSTGRES_DB
#
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-slate-postgres}"
: "${POSTGRES_USER:?set POSTGRES_USER}"
: "${POSTGRES_DB:?set POSTGRES_DB}"

dump="${1:?usage: restore-db.sh <path-to-dump.sql.gz>}"
[ -s "$dump" ] || { echo "FATAL: dump not found or empty: $dump" >&2; exit 1; }

echo "Restoring $dump into ${PG_CONTAINER}:${POSTGRES_DB} — this OVERWRITES current data."
read -r -p "Type the DB name to confirm: " confirm
[ "$confirm" = "$POSTGRES_DB" ] || { echo "aborted." >&2; exit 1; }

# The dump was taken with --clean --if-exists, so it drops+recreates objects.
gunzip -c "$dump" | docker exec -i "$PG_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "restore complete."
