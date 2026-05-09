#!/usr/bin/env sh
set -eu
PORT="${PORT:-8080}"

# Alembic for Postgres / Supabase; sqlite dev uses create_all in init_db().
if [ "${SKIP_ALEMBIC:-}" != "true" ]; then
  alembic -c components/issue_tracker_service/alembic.ini upgrade head
fi

exec uvicorn issue_tracker_service.main:app --host 0.0.0.0 --port "$PORT"
