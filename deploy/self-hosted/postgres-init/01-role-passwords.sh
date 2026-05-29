#!/bin/bash
# Set passwords for the Supabase service roles that the supabase/postgres
# image pre-creates with no password. Without this step, GoTrue,
# PostgREST and Storage cannot connect (they use these roles in their
# connection strings).
#
# Executed once at first container boot (Postgres convention:
# `/docker-entrypoint-initdb.d/*.sh` runs after the cluster is ready).
# Re-running on an existing volume is a no-op (Postgres skips initdb
# scripts when PGDATA is not empty).

set -euo pipefail

psql -v ON_ERROR_STOP=1 \
     --username "${POSTGRES_USER:-postgres}" \
     --dbname  "${POSTGRES_DB:-postgres}" <<EOSQL
    ALTER ROLE supabase_auth_admin    WITH PASSWORD '${POSTGRES_PASSWORD}';
    ALTER ROLE supabase_storage_admin WITH PASSWORD '${POSTGRES_PASSWORD}';
    ALTER ROLE authenticator           WITH PASSWORD '${POSTGRES_PASSWORD}';
    ALTER ROLE supabase_admin          WITH PASSWORD '${POSTGRES_PASSWORD}';
EOSQL

echo "[init] Role passwords set for supabase_auth_admin / authenticator / supabase_storage_admin / supabase_admin"
