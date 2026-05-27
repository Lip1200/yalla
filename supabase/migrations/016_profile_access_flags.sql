-- Migration 016 — Per-flag access toggles on profiles (#53)
--
-- Apply manually via the Supabase SQL editor.
--
-- Today the patient-app's 'Accès' sub-tab shows three toggles
-- (share_activity, share_challenges, share_restaurants) that the
-- frontend treated as local-only state — clicks never reached the
-- backend, no other surface honoured them. We persist them as plain
-- booleans on `profiles` so the doctor-side and the social feed can
-- filter by them in follow-up work.
--
-- Defaults to TRUE: existing rows keep their current visible behaviour
-- (which derived these flags from privacy_level). Patients can flip any
-- individual flag without changing their broader privacy_level.

alter table public.profiles
    add column if not exists share_activity    boolean not null default true,
    add column if not exists share_challenges  boolean not null default true,
    add column if not exists share_restaurants boolean not null default true;
