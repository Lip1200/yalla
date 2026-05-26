-- Migration 008 — RGPD consents (issue #35)
--
-- Apply manually via the Supabase SQL editor.
--
-- Append-only audit log of patient consent decisions. Each row is an
-- immutable state change (granted=true OR granted=false to revoke). The
-- "current" consent for a (patient, scope) pair is the most recent row.
-- This pattern satisfies RGPD audit requirements (we can prove WHAT was
-- consented, WHEN, and against which version of the text).
--
-- Used as a guard by:
--   - issue #23 (HealthKit / Health Connect) before reading device data
--   - issue #36 (health observations endpoint) before persisting metrics
--   - any future doctor-share or marketing endpoint

create table if not exists public.consents (
    id            serial      primary key,
    patient_id    integer     not null references public.profiles(id) on delete cascade,
    scope         text        not null,
    granted       boolean     not null,
    text_version  text        not null,
    recorded_at   timestamptz not null default now(),
    user_agent    text                  -- best-effort, optional
);

-- (patient_id, scope, recorded_at desc) index speeds up the "latest per
-- scope" query that powers GET /api/consents/me.
create index if not exists idx_consents_patient_scope_recorded
    on public.consents(patient_id, scope, recorded_at desc);
