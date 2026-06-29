#!/usr/bin/env bash
#
# Slate — Postgres backup to a gzipped dump + optional off-host copy.
#
# Single-VPS deployments have ONE disk: a failure, an accidental `docker volume
# rm`, or a bad `alembic downgrade` loses the entire database. This script takes
# a consistent `pg_dump`, gzips it, optionally ships it OFF the box (rclone), and
# prunes old local copies. Run it from the systemd timer in this directory.
#
# Config via environment (see infra/backup/backup.env.example):
#   PG_CONTAINER     container name running Postgres   (default: slate-postgres)
#   POSTGRES_USER    db user                            (REQUIRED)
#   POSTGRES_DB      db name                            (REQUIRED)
#   BACKUP_DIR       local staging dir                  (default: /var/backups/slate)
#   RCLONE_REMOTE    rclone target, e.g. "r2:slate-backups"; empty => local-only ⚠
#   RETENTION_DAYS   prune local dumps older than N     (default: 14)
#
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-slate-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/slate}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"

: "${POSTGRES_USER:?set POSTGRES_USER}"
: "${POSTGRES_DB:?set POSTGRES_DB}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
file="${BACKUP_DIR}/slate-${POSTGRES_DB}-${ts}.sql.gz"

# --clean --if-exists makes the dump self-contained and restorable over an
# existing DB; --no-owner avoids role-ownership mismatches on restore.
docker exec "$PG_CONTAINER" pg_dump \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner --clean --if-exists \
  | gzip -9 > "$file"

# Fail loudly if the dump is empty/truncated — a silent 0-byte "backup" is worse
# than none.
if [ ! -s "$file" ]; then
  echo "FATAL: backup file is empty: $file" >&2
  rm -f "$file"
  exit 1
fi
echo "wrote $(du -h "$file" | cut -f1) -> $file"

# Off-host copy. WITHOUT this, the backup lives on the same disk as the DB it
# protects — which defeats the purpose on a single VPS.
if [ -n "$RCLONE_REMOTE" ]; then
  rclone copy "$file" "${RCLONE_REMOTE}/" --no-traverse
  echo "uploaded -> ${RCLONE_REMOTE}/"
else
  echo "WARNING: RCLONE_REMOTE unset — backup is LOCAL-ONLY (same disk as the DB)." >&2
fi

# Prune old LOCAL dumps (off-host retention is the remote's lifecycle policy).
find "$BACKUP_DIR" -name "slate-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
