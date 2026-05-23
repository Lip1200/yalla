-- Migration to add image_url to feed_posts table

ALTER TABLE feed_posts ADD COLUMN IF NOT EXISTS image_url TEXT;
