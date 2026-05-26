-- Migration 006 — Doctor-specific fields on profiles
--
-- Apply manually via the Supabase SQL editor.
--
-- Until now, the doctor-specific fields (specialty, facility) only lived in
-- Supabase Auth user_metadata. The `DoctorProfile` schema returned by
-- /api/doctors/me already declares them as required fields, but
-- `_profile_row_to_doctor` was silently falling back to '' because the
-- columns did not exist.
--
-- We add nullable TEXT columns directly on `public.profiles` so the doctor
-- module becomes the source of truth (no extra Supabase Auth lookup needed
-- when building DoctorProfile responses).

alter table public.profiles
    add column if not exists specialty text not null default '',
    add column if not exists facility  text not null default '';
