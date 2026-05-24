-- Migration 005 — Badges et attribution (issue #22)
--
-- Apply manually via the Supabase SQL editor.
--
-- Couche gamification au-dessus des challenges (#21) :
--   - `badges` : catalogue des badges déblocables (templates statiques)
--   - `patient_badges` : badges effectivement gagnés par chaque patient
--     (clé primaire composite (patient_id, badge_id) garantit l'idempotence)
--
-- L'attribution se fait côté backend dans
-- `src/modules/challenges/service.py::evaluate_and_award_badges` quand une
-- assignation passe en status='completed'.

create table if not exists public.badges (
    id                   serial      primary key,
    code                 text        not null unique,
    name                 text        not null check (char_length(name) between 2 and 80),
    description          text        not null default '',
    icon                 text        not null default '🏅',
    criteria_kind        text        not null
        check (criteria_kind in ('first_completion', 'completion_count', 'category_completion')),
    criteria_threshold   integer     not null default 1 check (criteria_threshold >= 1),
    criteria_category    text,                -- non-null uniquement pour criteria_kind='category_completion'
    created_at           timestamptz not null default now()
);

create table if not exists public.patient_badges (
    patient_id           integer     not null references public.profiles(id)            on delete cascade,
    badge_id             integer     not null references public.badges(id)              on delete cascade,
    source_assignment_id integer              references public.patient_challenges(id)  on delete set null,
    earned_at            timestamptz not null default now(),
    primary key (patient_id, badge_id)
);

create index if not exists idx_patient_badges_patient on public.patient_badges(patient_id);

-- ===========================================================================
-- Seed : 4 badges de base (idempotent via ON CONFLICT)
-- ===========================================================================

insert into public.badges (code, name, description, icon, criteria_kind, criteria_threshold, criteria_category) values
    ('first_step',
     'Premier pas',
     'Tu as terminé ton tout premier défi. Bienvenue dans la communauté Yalla !',
     '🌱',
     'first_completion', 1, null),
    ('regular',
     'Régularité',
     'Tu as terminé 5 défis. Continue, tu construis une vraie habitude.',
     '🔥',
     'completion_count', 5, null),
    ('marathonien',
     'Marathonien',
     'Tu as terminé 10 défis. Impressionnant !',
     '🏆',
     'completion_count', 10, null),
    ('actif',
     'Actif·ve',
     'Tu as terminé 3 défis d''activité physique. Le mouvement, c''est ta force.',
     '🚶',
     'category_completion', 3, 'activity')
on conflict (code) do nothing;
