-- Migration 015 — Mutual-consent friendship (#55)
--
-- Apply manually via the Supabase SQL editor.
--
-- Adds a `status` column to `patient_friends` so adding someone creates a
-- pending request rather than an immediate friendship. The recipient
-- accepts or rejects via dedicated endpoints. The check constraint
-- restricts status to a small whitelist.
--
-- Default is 'accepted' so existing rows from the demo tests remain
-- visible without manual cleanup. New rows created via the friends
-- endpoint will explicitly insert 'pending'.

alter table public.patient_friends
    add column if not exists status text not null default 'accepted'
        check (status in ('pending', 'accepted', 'rejected', 'blocked'));

create index if not exists idx_patient_friends_status
    on public.patient_friends(status);
