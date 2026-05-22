-- Migration 002 — Challenges (Epic 5, issue #21)
--
-- Apply manually via the Supabase SQL editor. Adds the data model for the
-- gamification system: a catalogue of challenge templates (`challenges`) plus
-- the per-patient assignment table that tracks individual progress
-- (`patient_challenges`). Issue #22 will layer the podometer/badge validation
-- logic on top of these tables.

create table if not exists public.challenges (
    id            serial      primary key,
    title         text        not null check (char_length(title) between 2 and 120),
    description   text        not null default '',
    category      text        not null default 'activity',
    target_value  integer     not null check (target_value > 0),
    target_unit   text        not null default 'minutes',
    duration_days integer     not null default 7 check (duration_days between 1 and 90),
    difficulty    text        not null default 'medium' check (difficulty in ('easy','medium','hard')),
    is_template   boolean     not null default true,
    created_at    timestamptz not null default now()
);

create index if not exists idx_challenges_category   on public.challenges(category);
create index if not exists idx_challenges_difficulty on public.challenges(difficulty);

create table if not exists public.patient_challenges (
    id             serial      primary key,
    patient_id     integer     not null references public.profiles(id)  on delete cascade,
    challenge_id   integer     not null references public.challenges(id) on delete cascade,
    progress       integer     not null default 0   check (progress between 0 and 100),
    current_value  integer     not null default 0   check (current_value >= 0),
    started_at     timestamptz not null default now(),
    due_on         date        not null,
    completed_at   timestamptz,
    status         text        not null default 'active' check (status in ('active','completed','abandoned')),
    unique (patient_id, challenge_id, started_at)
);

create index if not exists idx_patient_challenges_patient on public.patient_challenges(patient_id);
create index if not exists idx_patient_challenges_status  on public.patient_challenges(status);
