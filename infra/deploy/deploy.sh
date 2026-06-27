#!/usr/bin/env bash
#
# DailyLoadout — migration-gated deploy (run ON the VPS, invoked by CD over SSH).
#
# The rule: try the migrations FIRST; if they fail, abort the deploy and keep the
# previous version serving. Order is the gate — migrations run BEFORE the service
# restart, so a failure never lets the new code take traffic.
#
#   1. back up the DB (recoverable if a migration succeeds-but-is-wrong)
#   2. record the current code SHA + alembic revision (for rollback)
#   3. fetch + check out the new code, install deps
#   4. `alembic upgrade head`  ── FAILS? restore old code, exit non-zero (no restart)
#                                 Postgres DDL is transactional, so a half-applied
#                                 migration auto-rolls-back to the prior revision.
#   5. restart api + worker
#   6. health-check; UNHEALTHY? downgrade schema + restore old code + restart
#
# Setup on the VPS (see docs/DEPLOYMENT.md §1.10):
#   - repo at $DL_REPO_DIR (default /opt/dailyloadout)
#   - the deploy user has passwordless sudo for: systemctl restart
#     dailyloadout-api dailyloadout-worker
#   - rclone + /etc/dailyloadout/backup.env configured (Phase 5 of PRELAUNCH)
#
set -euo pipefail

REPO_DIR="${DL_REPO_DIR:-/opt/dailyloadout}"
API_DIR="$REPO_DIR/packages/api"
HEALTH_URL="${DL_HEALTH_URL:-http://127.0.0.1:8100/health}"
SERVICES="dailyloadout-api dailyloadout-worker"

# What to deploy: a git ref — the tag `api/vX.Y.Z` in production, or
# `origin/main` in staging. Passed as $1 (or $SSH_ORIGINAL_COMMAND's last token
# when invoked via an authorized_keys forced command); defaults to origin/main.
REF="${1:-}"
if [ -z "$REF" ] && [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  _orig_args="${SSH_ORIGINAL_COMMAND#* }"
  [ "$_orig_args" != "$SSH_ORIGINAL_COMMAND" ] && REF="$_orig_args"
fi
REF="${REF:-origin/main}"

log() { echo "[deploy $(date -u +%H:%M:%SZ)] $*"; }
alembic() { (cd "$API_DIR" && poetry run alembic "$@"); }
restart() { sudo systemctl restart $SERVICES; }

cd "$REPO_DIR"

# 2. Snapshot current state for rollback.
PREV_SHA="$(git rev-parse HEAD)"
PREV_REV="$(alembic current 2>/dev/null | awk 'NR==1{print $1}')"
log "current: code=$PREV_SHA alembic=${PREV_REV:-<none>}"

restore_code() {
  log "restoring previous code ($PREV_SHA)"
  git checkout -f "$PREV_SHA"
  (cd "$API_DIR" && poetry install --without dev --no-interaction --no-root) || true
}

# 1. Back up first — a successful-but-wrong migration must be recoverable.
if [ -x "$REPO_DIR/infra/backup/backup-db.sh" ] && [ -f /etc/dailyloadout/backup.env ]; then
  log "pre-deploy backup"
  set -a; . /etc/dailyloadout/backup.env; set +a
  "$REPO_DIR/infra/backup/backup-db.sh" || { log "FATAL: backup failed — aborting deploy"; exit 1; }
fi

# 3. Fetch + check out the requested ref (tag in prod, origin/main in staging).
log "fetching + checking out $REF"
git fetch --quiet --tags --force origin
git checkout -f "$REF"
NEW_SHA="$(git rev-parse HEAD)"
if [ "$NEW_SHA" = "$PREV_SHA" ]; then
  log "no new commits — nothing to deploy"
  exit 0
fi
log "deploying $NEW_SHA"
(cd "$API_DIR" && poetry install --without dev --no-interaction --no-root)

# 4. THE GATE — migrate before any restart.
log "alembic upgrade head"
if ! alembic upgrade head; then
  log "MIGRATION FAILED — aborting deploy, previous version stays live"
  restore_code
  exit 1
fi

# 5. Restart services onto the new code.
log "restarting: $SERVICES"
restart

# 6. Health-check; roll back schema + code if the new version is unhealthy.
log "health check $HEALTH_URL"
healthy=0
for _ in $(seq 1 10); do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then healthy=1; break; fi
  sleep 3
done
if [ "$healthy" != "1" ]; then
  log "HEALTH CHECK FAILED — rolling back schema + code"
  if [ -n "${PREV_REV:-}" ]; then
    alembic downgrade "$PREV_REV" || log "WARN: downgrade failed (migration may be irreversible — restore from backup)"
  fi
  restore_code
  restart
  exit 1
fi

log "deploy OK — now at $NEW_SHA"
