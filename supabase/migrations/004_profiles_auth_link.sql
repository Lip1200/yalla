-- Migration 004 — Link profiles to Supabase Auth users (issue #27)
--
-- Apply manually via the Supabase SQL editor.
--
-- Adds a nullable auth_user_id column to public.profiles so a profile row can
-- be linked to a Supabase Auth user (auth.users.id is a UUID, but
-- profiles.id stays an int — we don't migrate the existing int IDs because
-- many tables reference them as FK (feed_posts.author_id, group_members.user_id,
-- patient_challenges.patient_id, etc.).
--
-- Nullable so existing demo rows (id 101, 102, ...) survive without a
-- linked auth user. ON DELETE SET NULL means deleting the auth user does
-- not cascade-delete the profile (medical data should outlive the account).

alter table public.profiles
    add column if not exists auth_user_id uuid unique
        references auth.users(id) on delete set null;

create index if not exists idx_profiles_auth_user_id
    on public.profiles(auth_user_id);
