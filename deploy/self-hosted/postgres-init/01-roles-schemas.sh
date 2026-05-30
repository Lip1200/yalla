#!/bin/bash
# Bootstrap the roles and schemas that GoTrue, PostgREST and Storage
# expect to find. Modeled on supabase/docker/volumes/db/{roles,jwt,
# realtime,webhooks,_supabase}.sql but trimmed to what we actually use
# (no Realtime, no Edge Functions, no webhooks, no Analytics).
#
# Idempotent — re-running on an existing DB is a no-op. Postgres only
# executes this once at first initdb anyway, but the SQL uses
# `IF NOT EXISTS` so a manual re-run works too.
#
# Runs as part of the standard /docker-entrypoint-initdb.d/ flow.

set -euo pipefail

psql -v ON_ERROR_STOP=1 \
     --username "${POSTGRES_USER:-postgres}" \
     --dbname  "${POSTGRES_DB:-postgres}" <<-EOSQL

    -- ── Roles FIRST ───────────────────────────────────────────────
    -- supabase/postgres has event triggers that try to reassign
    -- ownership of new extensions to supabase_admin, so this role
    -- must exist before CREATE EXTENSION can succeed.
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
            CREATE ROLE anon            NOLOGIN NOINHERIT;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
            CREATE ROLE authenticated   NOLOGIN NOINHERIT;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
            CREATE ROLE service_role    NOLOGIN NOINHERIT BYPASSRLS;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticator') THEN
            CREATE ROLE authenticator   LOGIN  NOINHERIT NOCREATEDB NOCREATEROLE NOSUPERUSER;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'supabase_admin') THEN
            CREATE ROLE supabase_admin  LOGIN  CREATEROLE CREATEDB REPLICATION BYPASSRLS;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'supabase_auth_admin') THEN
            CREATE ROLE supabase_auth_admin    LOGIN  NOINHERIT CREATEROLE NOCREATEDB;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'supabase_storage_admin') THEN
            CREATE ROLE supabase_storage_admin LOGIN  NOINHERIT CREATEROLE NOCREATEDB;
        END IF;
    END
    \$\$;

    -- ── Passwords ─────────────────────────────────────────────────
    ALTER ROLE authenticator           WITH PASSWORD '${POSTGRES_PASSWORD}';
    ALTER ROLE supabase_admin          WITH PASSWORD '${POSTGRES_PASSWORD}';
    ALTER ROLE supabase_auth_admin     WITH PASSWORD '${POSTGRES_PASSWORD}';
    ALTER ROLE supabase_storage_admin  WITH PASSWORD '${POSTGRES_PASSWORD}';

    -- ── PostgREST role membership ─────────────────────────────────
    GRANT anon, authenticated, service_role TO authenticator;

    -- ── Database-level CREATE (storage-api runs its own migrations) ─
    GRANT CREATE ON DATABASE postgres TO supabase_storage_admin;
    GRANT CREATE ON DATABASE postgres TO supabase_auth_admin;

    -- ── Schemas (created after roles so event triggers don't fail) ─
    CREATE SCHEMA IF NOT EXISTS auth            AUTHORIZATION supabase_auth_admin;
    CREATE SCHEMA IF NOT EXISTS storage         AUTHORIZATION supabase_storage_admin;
    CREATE SCHEMA IF NOT EXISTS extensions;
    CREATE SCHEMA IF NOT EXISTS graphql_public;

    -- Extensions intentionally omitted — our 18 migrations don't use
    -- any (no gen_random_uuid, no pgcrypto). GoTrue + Storage create
    -- whatever they need on their own first connection. Adding
    -- CREATE EXTENSION here trips the supautils event trigger in
    -- supabase/postgres which requires supabase_admin to be the
    -- connection user, not postgres.

    GRANT USAGE ON SCHEMA public        TO anon, authenticated, service_role;
    GRANT USAGE ON SCHEMA auth          TO anon, authenticated, service_role, supabase_auth_admin;
    GRANT USAGE ON SCHEMA storage       TO anon, authenticated, service_role, supabase_storage_admin;
    GRANT USAGE ON SCHEMA extensions    TO anon, authenticated, service_role;
    GRANT USAGE ON SCHEMA graphql_public TO anon, authenticated, service_role;

    -- service_role bypasses RLS, but PostgREST still needs explicit
    -- table-level grants when it lists tables. Default privileges
    -- cover future tables created in public.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public  GRANT ALL ON TABLES    TO anon, authenticated, service_role;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public  GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public  GRANT ALL ON FUNCTIONS TO anon, authenticated, service_role;

    -- ── JWT settings (read by helper functions some apps still use) ─
    ALTER DATABASE postgres SET "app.settings.jwt_secret" TO '${JWT_SECRET}';
    ALTER DATABASE postgres SET "app.settings.jwt_exp"    TO '${JWT_EXP:-3600}';
EOSQL

echo "[init] Supabase roles + schemas created, JWT settings applied"
