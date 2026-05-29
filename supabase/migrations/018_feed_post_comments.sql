-- Migration 018 — feed_post_comments
--
-- Apply manually via the Supabase SQL editor.
--
-- The patient-app exposes a comment composer under each feed post; up
-- to now the comments lived only in component state and vanished on
-- reload. This table persists them so they show up across devices and
-- so the `feed_posts.comments_count` denormalized counter can be
-- maintained by the service layer (mirrors the supports pattern).

create table if not exists public.feed_post_comments (
    id          serial      primary key,
    post_id     integer     not null references public.feed_posts(id) on delete cascade,
    author_id   integer     not null references public.profiles(id)   on delete cascade,
    content     text        not null check (char_length(content) between 1 and 1000),
    created_at  timestamptz not null default now()
);

create index if not exists idx_feed_post_comments_post on public.feed_post_comments(post_id, created_at desc);
create index if not exists idx_feed_post_comments_author on public.feed_post_comments(author_id);
