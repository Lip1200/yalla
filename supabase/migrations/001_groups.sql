-- Migration 001 — Community groups (Epic 4, issue #16)
--
-- Apply manually via the Supabase SQL editor. There is no automated migration
-- runner in this project yet; each numbered file represents one atomic schema
-- change that should be applied once, in order.

create table if not exists public.groups (
    id          serial primary key,
    name        text        not null check (char_length(name) between 2 and 100),
    description text        not null default '',
    category    text        not null default 'general',
    creator_id  integer     not null references public.profiles(id) on delete cascade,
    created_at  timestamptz not null default now()
);

create table if not exists public.group_members (
    group_id  integer     not null references public.groups(id) on delete cascade,
    user_id   integer     not null references public.profiles(id) on delete cascade,
    role      text        not null default 'member' check (role in ('admin', 'member')),
    joined_at timestamptz not null default now(),
    primary key (group_id, user_id)
);

create index if not exists idx_group_members_user on public.group_members(user_id);
create index if not exists idx_groups_category    on public.groups(category);
