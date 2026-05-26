-- Migration 013 — Make profiles.age nullable
--
-- Apply manually via the Supabase SQL editor.
--
-- The age column was created as NOT NULL in the original profiles schema,
-- predating any of the repo migrations. This blocks `_ensure_profile_for_auth_user`
-- from inserting a freshly-signed-up doctor profile (doctors don't have a
-- patient-style age; patients fill it later via PATCH /api/users/{id}).
--
-- Making it nullable removes the silent failure and matches the rest of the
-- optional patient fields (primary_goal, last_check_in, status, etc.) which
-- are already nullable.

alter table public.profiles
    alter column age drop not null;
