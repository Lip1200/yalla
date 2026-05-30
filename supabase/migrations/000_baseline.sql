-- Migration 000 — Baseline schema (the tables our 18 numbered
-- migrations assume to already exist)
--
-- Background
-- ----------
-- When this project was bootstrapped, `profiles` and `feed_posts` were
-- created via the Supabase Studio UI rather than via SQL — so they
-- never made it into our versioned migrations folder. The 18 numbered
-- migrations all alter / extend those tables but none of them creates
-- them, which means a fresh Postgres (self-hosted stack, dev VM, new
-- Supabase project) cannot be brought up to date by replaying
-- supabase/migrations/*.sql alone.
--
-- This file backfills that gap so the migrations are self-sufficient
-- against any blank database. It captures the column names and types
-- the application service layer reads/writes (cf.
-- src/modules/doctors/service.py:_row_to_detail and
-- src/modules/social/service.py:_row_to_post). Optional columns added
-- by later migrations (auth_user_id, share_*, specialty, facility,
-- comments_count) are NOT recreated here — they live in their own
-- numbered migration and must be applied after this one.

create table if not exists public.profiles (
    id                          integer    primary key,
    full_name                   text       not null,
    role                        text       not null default 'patient',
    privacy_level               text       not null default 'Partage sélectif',
    primary_goal                text       not null default '',
    age                         integer,
    weekly_activity_minutes     integer    not null default 0,
    challenge_completion_rate   integer    not null default 0,
    activity_completion_rate    integer    not null default 0,
    has_app_access              boolean    not null default true,
    last_check_in               date,
    status                      text,
    care_notes                  text[]     not null default '{}',
    doctor_notes                text[]     not null default '{}'
);

create table if not exists public.feed_posts (
    id                  serial      primary key,
    author_id           integer     not null references public.profiles(id) on delete cascade,
    author_name         text        not null,
    author_role         text        not null,
    type                text        not null check (type in ('post','achievement')),
    content             text        not null,
    achievement_label   text,
    likes               integer     not null default 0,
    created_at          timestamptz not null default now()
);

create index if not exists idx_feed_posts_created_at on public.feed_posts(created_at desc);
create index if not exists idx_feed_posts_author     on public.feed_posts(author_id);
