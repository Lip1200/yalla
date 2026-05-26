-- Migration 012 — Storage bucket for feed images (issue #32)
--
-- Apply manually via the Supabase SQL editor. Unlike previous migrations
-- this one touches the `storage` schema rather than `public`.
--
-- Replaces the previous "base64 inside a TEXT column" hack with a real
-- Supabase Storage bucket. The backend now decodes the base64 payload
-- the mobile app sends, uploads the binary to this bucket, and stores
-- only the resulting public URL in `feed_posts.image_url`.
--
-- The bucket is public-read so any client can render the image via the
-- URL without an auth header. Uploads are gated by an RLS policy that
-- accepts both anon (the FastAPI backend uses the publishable key) and
-- authenticated callers — tighten this if a future move to a service
-- role key is decided.

insert into storage.buckets (id, name, public)
values ('feed-images', 'feed-images', true)
on conflict (id) do nothing;

-- Idempotent re-application: drop + create instead of `if not exists`
-- (Postgres doesn't support that on CREATE POLICY).

drop policy if exists "feed_images_public_read" on storage.objects;
create policy "feed_images_public_read"
on storage.objects
for select
using (bucket_id = 'feed-images');

drop policy if exists "feed_images_anon_insert" on storage.objects;
create policy "feed_images_anon_insert"
on storage.objects
for insert
with check (bucket_id = 'feed-images');

drop policy if exists "feed_images_anon_delete" on storage.objects;
create policy "feed_images_anon_delete"
on storage.objects
for delete
using (bucket_id = 'feed-images');
