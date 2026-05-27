-- Migration 014 — Friendship persistence between patients (#45)
--
-- Apply manually via the Supabase SQL editor.
--
-- Directed friendship model: (patient_id, friend_id) means "patient_id
-- added friend_id to their friends list". Asymmetric: A adding B does not
-- automatically mean B added A. Keeps the implementation simple for the
-- MVP and avoids consent ambiguity (B can ignore the connection until
-- they also add A).
--
-- A future migration may introduce a "pending"/"accepted" status if we
-- want a request → accept flow.

create table if not exists public.patient_friends (
    patient_id integer     not null references public.profiles(id) on delete cascade,
    friend_id  integer     not null references public.profiles(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (patient_id, friend_id),
    check (patient_id <> friend_id)
);

create index if not exists idx_patient_friends_patient on public.patient_friends(patient_id);
create index if not exists idx_patient_friends_friend  on public.patient_friends(friend_id);
