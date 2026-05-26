-- Migration 011 — Messaging backend (issue #20)
--
-- Apply manually via the Supabase SQL editor.
--
-- Three tables to back the existing MessagesScreen in patient-app:
--
--   conversations            — a chat container (1-on-1 today, group later)
--   conversation_participants — who can read/write each conversation
--   messages                 — actual content, ordered by sent_at
--
-- Currently the patient-app/MessagesScreen reads conversations from a
-- hardcoded demo dict in patients/service.py — those will keep working
-- as fixtures until the frontend migrates to the new endpoints.

create table if not exists public.conversations (
    id         serial      primary key,
    kind       text        not null default 'direct' check (kind in ('direct', 'group')),
    title      text                 null,
    created_at timestamptz not null default now()
);

create table if not exists public.conversation_participants (
    conversation_id integer     not null references public.conversations(id) on delete cascade,
    user_id         integer     not null references public.profiles(id)     on delete cascade,
    joined_at       timestamptz not null default now(),
    last_read_at    timestamptz,
    primary key (conversation_id, user_id)
);

create index if not exists idx_conversation_participants_user
    on public.conversation_participants(user_id);

create table if not exists public.messages (
    id              serial      primary key,
    conversation_id integer     not null references public.conversations(id) on delete cascade,
    sender_id       integer     not null references public.profiles(id),
    content         text        not null check (char_length(content) between 1 and 2000),
    sent_at         timestamptz not null default now()
);

-- (conversation_id, sent_at desc) dominates: list a thread newest-first
-- + filter for unread count.
create index if not exists idx_messages_conversation_sent
    on public.messages(conversation_id, sent_at desc);
