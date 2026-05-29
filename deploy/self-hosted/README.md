# Self-hosted Supabase stack (Path A)

Drop-in replacement for the Supabase cloud dependency. The backend keeps
talking to `supabase_client.table(...)` and `supabase_client.auth.*`
exactly as it does today — only the env vars change.

## What this folder contains

| File | Purpose |
|---|---|
| `docker-compose.override.yml` | Adds Postgres + GoTrue + PostgREST + Storage + Kong + Studio to the existing compose graph |
| `.env.example` | Template for the secrets the override needs |
| `kong.yml` | Declarative gateway routing — fans `/auth/v1/*`, `/rest/v1/*`, `/storage/v1/*` to the right service |
| `postgres-init/01-role-passwords.sh` | Sets passwords on the Supabase service roles at first DB boot |
| `scripts/gen-jwt.py` | Generates the `ANON_KEY` + `SERVICE_ROLE_KEY` JWTs from `JWT_SECRET` |
| `scripts/migrate-from-cloud.sh` | One-shot `pg_dump` from the cloud project into the local DB |

## Quick start

```bash
# 0) On the droplet, in /opt/yalla
cd /opt/yalla

# 1) Prep .env
cp deploy/self-hosted/.env.example deploy/self-hosted/.env
POSTGRES_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 32)
DASHBOARD_PASSWORD=$(openssl rand -hex 16)

# Fill those values in deploy/self-hosted/.env, then generate the JWT keys:
uv run python deploy/self-hosted/scripts/gen-jwt.py "$JWT_SECRET"
# Paste the two output lines (ANON_KEY=… and SERVICE_ROLE_KEY=…) into .env

# 2) Boot the stack
docker compose \
    -f docker-compose.yml \
    -f deploy/self-hosted/docker-compose.override.yml \
    --env-file deploy/self-hosted/.env \
    up -d

# 3) Apply the 18 SQL migrations (idempotent)
for f in supabase/migrations/*.sql; do
    docker compose exec -T db psql -U postgres -d postgres < "$f"
done

# 4) (Optional) Copy existing data from the cloud project
export CLOUD_DB_URL="postgres://postgres.<ref>:<password>@aws-0-…:5432/postgres"
bash deploy/self-hosted/scripts/migrate-from-cloud.sh

# 5) Restart the backend so it picks up the new SUPABASE_URL/KEY
docker compose restart backend

# 6) Smoke-test
curl https://46-101-16-132.nip.io/docs
```

## What this changes for the application

**Nothing.** `supabase-py` accepts any URL + bearer that points to a
Supabase-compatible stack (PostgREST + GoTrue at the same Kong gateway).
The `restore_service_bearer` quirk documented in
`report/08-annexes.md` §8.2 still applies — same client library, same
behavior.

The only env vars to change in `/opt/yalla/.env`:

```diff
- SUPABASE_URL=https://srwnhbczslthjdnlbtqw.supabase.co
- SUPABASE_KEY=sb_secret_…
+ SUPABASE_URL=http://kong:8000
+ SUPABASE_KEY=<SERVICE_ROLE_KEY from gen-jwt.py>
```

## Resource footprint

| Service | RAM at idle |
|---|---|
| db (Postgres) | ~250 MB |
| auth (GoTrue) | ~80 MB |
| rest (PostgREST) | ~40 MB |
| storage | ~120 MB |
| kong | ~250 MB |
| studio (optional) | ~250 MB |
| meta (optional) | ~50 MB |
| **subtotal Supabase** | **~700 MB without studio, ~1 GB with** |
| backend + doctor-web + caddy | ~250 MB |
| **droplet total** | **~1 GB → ~1.3 GB** |

The current 1 vCPU / 1 GB droplet **will OOM**. Upgrade to a 2 vCPU /
2 GB plan (~12 €/mo) before switching.

## Backups

The cloud Supabase backups stop applying. Add a simple cron job on the
droplet:

```bash
# /etc/cron.daily/yalla-pg-backup
docker compose -f /opt/yalla/docker-compose.yml exec -T db \
    pg_dump -U postgres -Fc -f /var/backups/yalla-$(date +%F).dump postgres
find /var/backups -name 'yalla-*.dump' -mtime +30 -delete
```

## Rollback path

If something goes wrong, point `SUPABASE_URL` back at the cloud
project and `docker compose restart backend`. The data in the cloud
project is untouched (the migration script is one-way; it reads but
doesn't write to the cloud DB).
