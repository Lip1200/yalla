-- Migration 009 — Health observations (issue #36)
--
-- Apply manually via the Supabase SQL editor.
--
-- Append-only store of patient health metrics outside the challenges
-- mechanic. Complements the per-challenge progress logs of #22 with a
-- longitudinal feed of vital signs and biometrics that the doctor
-- dashboard, the recommendation engine, and the patient progress views
-- can all read from.
--
-- Each `kind` value maps to a consent scope (see ConsentScope in
-- src/modules/consents/schemas.py) — write access is gated by that
-- consent at the service layer.

create table if not exists public.health_observations (
    id           serial      primary key,
    patient_id   integer     not null references public.profiles(id) on delete cascade,
    kind         text        not null,
    value        numeric     not null,
    unit         text        not null,
    recorded_at  timestamptz not null,
    source       text        not null default 'manual',
    created_at   timestamptz not null default now()
);

-- (patient, kind, recorded_at desc) is the dominant query — both the
-- patient progress view and the doctor latest-per-kind read benefit.
create index if not exists idx_health_observations_patient_kind_recorded
    on public.health_observations(patient_id, kind, recorded_at desc);
