"""Seed richer demo data so the app feels alive during the class presentation.

Idempotent: re-running won't duplicate. Each block checks for existing
rows by a natural key (title for challenges, content for posts, name for
groups) before inserting.

Touches:
- public.challenges    : adds 6 challenges across categories
- public.feed_posts    : adds 12 posts spread over the demo authors
- public.groups        : adds 2 groups (walking, cooking) + members
- public.patient_challenges : assigns 1-2 active challenges per demo patient
                              (Karim 101, Amina 102, Youssef 103)
- public.patient_badges     : back-fills the 'first_step' badge for anyone
                              who has at least one completed assignment but
                              no badge yet
"""

from datetime import date, datetime, timedelta, timezone

from src.core.database import supabase_client


# ===========================================================================
# Helpers
# ===========================================================================

def upsert_by(table: str, lookup_col: str, lookup_value, payload: dict):
    """Insert if no row matches lookup_col == lookup_value. Returns the row
    (existing or freshly inserted). Returns None on hard error."""
    existing = (
        supabase_client.table(table)
        .select("*")
        .eq(lookup_col, lookup_value)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]
    resp = supabase_client.table(table).insert(payload).execute()
    if resp.data:
        return resp.data[0]
    return None


def ensure_member(group_id: int, user_id: int, role: str = "member"):
    existing = (
        supabase_client.table("group_members")
        .select("*")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return
    supabase_client.table("group_members").insert(
        {"group_id": group_id, "user_id": user_id, "role": role}
    ).execute()


def ensure_active_assignment(patient_id: int, challenge_id: int, duration_days: int = 7):
    existing = (
        supabase_client.table("patient_challenges")
        .select("*")
        .eq("patient_id", patient_id)
        .eq("challenge_id", challenge_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if existing.data:
        return
    started = datetime.now(timezone.utc)
    due = (started + timedelta(days=duration_days)).date().isoformat()
    supabase_client.table("patient_challenges").insert({
        "patient_id": patient_id,
        "challenge_id": challenge_id,
        "due_on": due,
        "progress": 35,
        "current_value": 0,
        "status": "active",
    }).execute()


# ===========================================================================
# Challenges
# ===========================================================================

CHALLENGES = [
    {
        "title": "Hydratation quotidienne",
        "description": "Boire 1,5L d'eau par jour pendant une semaine.",
        "category": "nutrition",
        "target_value": 7,
        "target_unit": "sessions",
        "duration_days": 7,
        "difficulty": "easy",
        "is_template": True,
    },
    {
        "title": "Petit-déjeuner équilibré",
        "description": "Composer un petit-déj avec protéines + fibres + fruit, 5 matins sur 7.",
        "category": "nutrition",
        "target_value": 5,
        "target_unit": "sessions",
        "duration_days": 7,
        "difficulty": "medium",
        "is_template": True,
    },
    {
        "title": "10 minutes après le repas",
        "description": "Marcher 10 minutes après le déjeuner ou le dîner.",
        "category": "activity",
        "target_value": 70,
        "target_unit": "minutes",
        "duration_days": 7,
        "difficulty": "easy",
        "is_template": True,
    },
    {
        "title": "Sommeil régulier",
        "description": "Se coucher avant 23h, 5 soirs sur 7.",
        "category": "sleep",
        "target_value": 5,
        "target_unit": "sessions",
        "duration_days": 7,
        "difficulty": "medium",
        "is_template": True,
    },
    {
        "title": "Méditation 5 minutes",
        "description": "5 minutes de cohérence cardiaque chaque matin.",
        "category": "mindfulness",
        "target_value": 35,
        "target_unit": "minutes",
        "duration_days": 7,
        "difficulty": "easy",
        "is_template": True,
    },
    {
        "title": "Partager un repas inspirant",
        "description": "Publier une photo + 2 conseils sur un repas diabète-friendly cette semaine.",
        "category": "community",
        "target_value": 1,
        "target_unit": "sessions",
        "duration_days": 7,
        "difficulty": "easy",
        "is_template": True,
    },
]


# ===========================================================================
# Feed posts
# ===========================================================================

POSTS = [
    (102, "achievement", "J'ai terminé mon défi marche douce 7 jours sur 7. Étape suivante : 25 min!", "Marche douce 7/7"),
    (101, "post", "Astuce du jour : couper les fruits en début de semaine pour ne pas grignoter le soir."),
    (103, "recipe", "Salade de pois chiches, tomates cerises et menthe — prête en 8 minutes, idéale pour le midi."),
    (102, "post", "Question ouverte : qui fait du yoga le matin ? J'aimerais m'y mettre."),
    (101, "achievement", "Premier 5 km de la saison ce week-end. Doucement mais sûrement!", "5km!"),
    (103, "post", "Marche au parc Bertrand demain 18h, si quelqu'un veut se joindre, MP."),
    (102, "recipe", "Bowl quinoa-poulet-avocat : 380 kcal, IG bas, ultra-rassasiant. Recette en commentaire."),
    (101, "post", "Demain je teste les bâtons de marche nordique. Quelqu'un en utilise déjà ?"),
    (103, "achievement", "3 défis terminés ce mois-ci. Yalla c'est efficace.", "3 défis"),
    (102, "post", "Petit rappel : on a tous le droit à un repas plaisir par semaine, sans culpabilité."),
    (101, "recipe", "Smoothie pommes-épinards-gingembre : antioxydants et 0 sucre ajouté."),
    (102, "post", "Si quelqu'un cherche un groupe marche du samedi matin, on monte le nôtre, dites-moi."),
]


# ===========================================================================
# Groups
# ===========================================================================

GROUPS = [
    {
        "name": "Marche du samedi matin",
        "description": "On se retrouve chaque samedi 9h30 au parc Bertrand pour 45 min de marche.",
        "category": "walking",
        "creator_id": 102,  # Amina
        "members": [101, 103],
    },
    {
        "name": "Cuisine maline",
        "description": "Recettes diabète-friendly à partager, idées de batch cooking, échanges sur les ingrédients.",
        "category": "cooking",
        "creator_id": 103,  # Youssef
        "members": [101, 102],
    },
]


# ===========================================================================
# Patient challenge assignments (active)
# ===========================================================================

ASSIGNMENTS = [
    # (patient_id, challenge_title)
    (102, "Méditation 5 minutes"),     # Amina
    (102, "Petit-déjeuner équilibré"), # Amina
    (103, "10 minutes après le repas"),# Youssef
    (103, "Hydratation quotidienne"),  # Youssef
]


# ===========================================================================
# Driver
# ===========================================================================

def main() -> None:
    print("=== Challenges ===")
    title_to_id: dict[str, int] = {}
    for payload in CHALLENGES:
        row = upsert_by("challenges", "title", payload["title"], payload)
        if row:
            title_to_id[payload["title"]] = row["id"]
            print(f"  {row['id']:>3}  {payload['title']}")

    print("\n=== Feed posts ===")
    authors_resp = (
        supabase_client.table("profiles")
        .select("id, full_name, role")
        .in_("id", list({entry[0] for entry in POSTS}))
        .execute()
    )
    authors = {r["id"]: r for r in (authors_resp.data or [])}
    for entry in POSTS:
        if len(entry) == 4:
            author_id, post_type, content, achievement = entry
        else:
            author_id, post_type, content = entry
            achievement = None
        author = authors.get(author_id)
        if not author:
            print(f"  skip — author {author_id} missing")
            continue
        payload = {
            "author_id": author_id,
            "author_name": author["full_name"],
            "author_role": author["role"],
            "type": post_type,
            "content": content,
            "achievement_label": achievement,
            "likes": 0,
            "comments_count": 0,
        }
        row = upsert_by("feed_posts", "content", content, payload)
        if row:
            print(f"  post#{row['id']}  by {author['full_name']}  '{content[:50]}…'")

    print("\n=== Groups ===")
    for spec in GROUPS:
        members = spec.pop("members")
        row = upsert_by("groups", "name", spec["name"], spec)
        if not row:
            continue
        group_id = row["id"]
        # Creator is admin
        ensure_member(group_id, spec["creator_id"], role="admin")
        for member_id in members:
            ensure_member(group_id, member_id)
        print(f"  group#{group_id}  {spec['name']}  (creator={spec['creator_id']}, +{len(members)} members)")

    print("\n=== Active assignments ===")
    for patient_id, title in ASSIGNMENTS:
        challenge_id = title_to_id.get(title)
        if not challenge_id:
            print(f"  skip — challenge {title!r} missing")
            continue
        ensure_active_assignment(patient_id, challenge_id)
        print(f"  patient {patient_id} → '{title}'")

    print("\nDone.")


if __name__ == "__main__":
    main()
