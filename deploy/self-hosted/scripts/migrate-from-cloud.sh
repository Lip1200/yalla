#!/bin/bash
# One-shot migration: copies all schemas + data from the Supabase cloud
# instance into the local self-hosted Postgres container.
#
# Prerequisites
# -------------
# 1. The self-hosted stack must already be running:
#       docker compose -f docker-compose.yml \
#                      -f deploy/self-hosted/docker-compose.override.yml \
#                      --env-file deploy/self-hosted/.env \
#                      up -d db
# 2. You need the cloud DB connection string (Project Settings →
#    Database → Connection string → URI):
#       postgres://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
#
# Usage
# -----
#   export CLOUD_DB_URL="postgres://postgres.srwnhbczslthjdnlbtqw:…@…:5432/postgres"
#   bash deploy/self-hosted/scripts/migrate-from-cloud.sh
#
# What it does
# ------------
# - pg_dump of the `public`, `auth.users`, and `storage.*` schemas.
# - Streams the dump into `docker compose exec db psql`.
# - Skips ownership re-assignment (the local roles differ from cloud).
#
# Caveats
# -------
# - Existing data in the local DB is REPLACED for the listed schemas.
# - Storage object content stays on the cloud — you have to re-upload
#   the bucket files manually (or run `supabase storage cp` against
#   the cloud, then re-upload to the local Storage service).

set -euo pipefail

: "${CLOUD_DB_URL:?Set CLOUD_DB_URL to the Supabase cloud connection string}"

echo "[1/3] Dumping public + auth.users + storage.* from cloud…"
pg_dump \
    --no-owner \
    --no-privileges \
    --schema=public \
    --schema=auth \
    --schema=storage \
    --data-only \
    --column-inserts \
    "$CLOUD_DB_URL" \
    > /tmp/yalla-cloud-dump.sql

SIZE=$(wc -c < /tmp/yalla-cloud-dump.sql)
echo "[1/3] Dump complete — $SIZE bytes at /tmp/yalla-cloud-dump.sql"

echo "[2/3] Applying our versioned migrations against the local DB…"
for f in supabase/migrations/*.sql; do
    echo "      → $(basename "$f")"
    docker compose exec -T db psql -U postgres -d postgres < "$f"
done

echo "[3/3] Streaming the cloud data into the local DB…"
docker compose exec -T db psql -U postgres -d postgres < /tmp/yalla-cloud-dump.sql

echo
echo "Done. Verify with:"
echo "  docker compose exec db psql -U postgres -c 'select count(*) from profiles;'"
