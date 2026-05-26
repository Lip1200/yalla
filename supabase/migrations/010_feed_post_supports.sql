-- Migration 010 — feed_post_supports for per-user like idempotency (issue #29)
--
-- Apply manually via the Supabase SQL editor.
--
-- Before this change, `feed_posts.likes` was a single counter that any
-- caller could increment N times — a user could "like" the same post
-- repeatedly and inflate the score. The new `feed_post_supports` table
-- ties each like to a (post, user) pair with a composite primary key,
-- making double-likes impossible at the database level.
--
-- The denormalized `feed_posts.likes` counter is kept for read
-- performance (no JOIN needed on feed listing) and is maintained by the
-- service layer on every add/remove.

create table if not exists public.feed_post_supports (
    post_id    integer     not null references public.feed_posts(id) on delete cascade,
    user_id    integer     not null references public.profiles(id)   on delete cascade,
    created_at timestamptz not null default now(),
    primary key (post_id, user_id)
);

create index if not exists idx_feed_post_supports_user on public.feed_post_supports(user_id);
