-- Migration 007 — Account setup tokens (issue #33)
--
-- Apply manually via the Supabase SQL editor.
--
-- Replaces the previous create-patient-account flow that generated a temp
-- password server-side and persisted it in plaintext in `profiles.care_notes`.
-- The new flow defers credential creation to the patient: the doctor
-- receives a one-shot invitation URL containing this token, the patient
-- opens it, picks their own password, and only then the Supabase Auth user
-- gets created and linked to the pre-provisioned profile row.

create table if not exists public.account_setup_tokens (
    token        text        primary key,
    patient_id   integer     not null references public.profiles(id) on delete cascade,
    email        text        not null,
    created_at   timestamptz not null default now(),
    expires_at   timestamptz not null,
    used_at      timestamptz
);

create index if not exists idx_account_setup_tokens_patient on public.account_setup_tokens(patient_id);
create index if not exists idx_account_setup_tokens_expires on public.account_setup_tokens(expires_at);
