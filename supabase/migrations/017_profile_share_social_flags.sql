-- Migration 017 — Extra per-flag access toggles on profiles (social + DM)
--
-- Apply manually via the Supabase SQL editor.
--
-- The patient-app 'Accès' sub-tab exposes two more switches that were
-- never persisted: "Partager mon activité sociale" (feed) and "Partager
-- mes messages avec l'expert". Add them with the same shape as the
-- existing share_* flags (see migration 016).
--
-- Defaults to TRUE: existing rows keep their current visible behaviour.

alter table public.profiles
    add column if not exists share_posts                  boolean not null default true,
    add column if not exists share_messages_with_expert   boolean not null default true;
