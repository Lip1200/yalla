from datetime import date, datetime

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.patients.schemas import (
    AppRole,
    Challenge,
    Conversation,
    FeedPost,
    FeedPostCreate,
    PatientProfile,
    PatientSettings,
    PostType,
    PrivacySettingsUpdate,
    Progression,
    SessionKind,
    SupportSession,
    SupportSessionCreate,
)

challenges: dict[int, list[Challenge]] = {
    101: [
        Challenge(
            id=1,
            title="20 minutes de marche",
            description="Marcher 5 jours cette semaine après le déjeuner.",
            category="Activité",
            progress=70,
            due_on=date(2026, 5, 3),
        ),
        Challenge(
            id=2,
            title="Petit-déjeuner IG bas",
            description="Préparer 4 petits-déjeuners avec fibres et protéines.",
            category="Alimentation",
            progress=45,
            due_on=date(2026, 5, 1),
        ),
    ],
    102: [
        Challenge(
            id=3,
            title="Animer le groupe marche",
            description="Organiser une sortie collective et relancer les participants.",
            category="Accompagnement",
            progress=90,
            due_on=date(2026, 4, 30),
        ),
        Challenge(
            id=4,
            title="Partager un conseil repas",
            description="Publier deux idées de repas équilibrés pour le groupe.",
            category="Communauté",
            progress=80,
            due_on=date(2026, 5, 2),
        ),
    ],
}



conversations: dict[int, list[Conversation]] = {
    101: [
        Conversation(
            id=1,
            contact_name="Amina Saidi",
            contact_role=AppRole.EXPERT_PATIENT,
            last_message="On peut adapter ton défi marche pour demain.",
            unread_count=1,
            updated_at=datetime(2026, 4, 27, 16, 45),
        ),
        Conversation(
            id=2,
            contact_name="Groupe marche du samedi",
            contact_role=AppRole.EXPERT_PATIENT,
            last_message="Rendez-vous à 9h30 devant le parc.",
            unread_count=0,
            updated_at=datetime(2026, 4, 26, 20, 15),
        ),
    ],
    102: [
        Conversation(
            id=3,
            contact_name="Karim El Mansouri",
            contact_role=AppRole.PATIENT,
            last_message="Merci pour le conseil sur le petit-déjeuner.",
            unread_count=0,
            updated_at=datetime(2026, 4, 27, 15, 25),
        ),
    ],
}


def get_profile(patient_id: int) -> PatientProfile:
    response = supabase_client.table("profiles").select("*").eq("id", patient_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    return _row_to_profile(response.data[0])


def list_feed(patient_id: int, limit: int = 20, offset: int = 0) -> list[FeedPost]:
    get_profile(patient_id)
    # Apply standard Supabase pagination range slicing: range(offset, offset + limit - 1)
    response = (
        supabase_client.table("feed_posts")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    posts = []
    for row in response.data:
        created_at_str = row["created_at"]
        created_at_dt = (
            datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime.now()
        )
        role = AppRole.EXPERT_PATIENT if row["author_role"] == "expert_patient" else AppRole.PATIENT
        post_type = PostType.ACHIEVEMENT if row["type"] == "achievement" else PostType.POST

        posts.append(
            FeedPost(
                id=row["id"],
                author_id=row["author_id"],
                author_name=row["author_name"],
                author_role=role,
                type=post_type,
                content=row["content"],
                achievement_label=row.get("achievement_label"),
                likes=row["likes"],
                comments_count=row["comments_count"],
                created_at=created_at_dt,
            )
        )
    return posts


def create_post(patient_id: int, payload: FeedPostCreate) -> FeedPost:
    profile = get_profile(patient_id)

    insert_data = {
        "author_id": profile.id,
        "author_name": profile.full_name,
        "author_role": profile.role.value,
        "type": payload.type.value,
        "content": payload.content,
        "achievement_label": payload.achievement_label,
        "likes": 0,
        "comments_count": 0,
    }

    response = supabase_client.table("feed_posts").insert(insert_data).execute()
    row = response.data[0]

    created_at_str = row["created_at"]
    created_at_dt = (
        datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        if created_at_str
        else datetime.now()
    )

    return FeedPost(
        id=row["id"],
        author_id=row["author_id"],
        author_name=row["author_name"],
        author_role=profile.role,
        type=payload.type,
        content=row["content"],
        achievement_label=row.get("achievement_label"),
        likes=row["likes"],
        comments_count=row["comments_count"],
        created_at=created_at_dt,
    )


def get_progression(patient_id: int) -> Progression:
    profile = get_profile(patient_id)
    return Progression(
        weekly_activity_minutes=profile.weekly_activity_minutes,
        challenge_completion_rate=profile.challenge_completion_rate,
        current_streak_days=6 if profile.role == AppRole.EXPERT_PATIENT else 3,
        active_challenges=challenges.get(patient_id, []),
    )





def list_conversations(patient_id: int) -> list[Conversation]:
    get_profile(patient_id)
    return sorted(conversations.get(patient_id, []), key=lambda item: item.updated_at, reverse=True)


def get_settings(patient_id: int) -> PatientSettings:
    profile = get_profile(patient_id)
    is_private = profile.privacy_level == "Données privées"
    return PatientSettings(
        profile=profile,
        share_activity=not is_private,
        share_challenges=not is_private,
        share_restaurants=profile.privacy_level != "Données privées",
    )


def update_privacy(patient_id: int, payload: PrivacySettingsUpdate) -> PatientSettings:
    get_profile(patient_id)
    supabase_client.table("profiles").update({"privacy_level": payload.privacy_level}).eq("id", patient_id).execute()
    return get_settings(patient_id)


def list_sessions(patient_id: int) -> list[SupportSession]:
    profile = get_profile(patient_id)
    _ensure_expert(profile)

    response = (
        supabase_client.table("support_sessions")
        .select("*")
        .eq("expert_patient_id", patient_id)
        .order("scheduled_for", desc=False)
        .execute()
    )

    res = []
    for row in response.data:
        sched_str = row["scheduled_for"]
        sched_dt = (
            datetime.fromisoformat(sched_str.replace("Z", "+00:00"))
            if sched_str
            else datetime.now()
        )
        kind = SessionKind.GROUP if row["kind"] == "group" else SessionKind.INDIVIDUAL

        res.append(
            SupportSession(
                id=row["id"],
                expert_patient_id=row["expert_patient_id"],
                title=row["title"],
                kind=kind,
                scheduled_for=sched_dt,
                capacity=row["capacity"],
                enrolled_count=row["enrolled_count"],
                notes=row.get("notes") or "",
            )
        )
    return res


def create_session(patient_id: int, payload: SupportSessionCreate) -> SupportSession:
    profile = get_profile(patient_id)
    _ensure_expert(profile)

    insert_data = {
        "expert_patient_id": patient_id,
        "title": payload.title,
        "kind": payload.kind.value,
        "scheduled_for": payload.scheduled_for.isoformat(),
        "capacity": payload.capacity,
        "enrolled_count": 0,
        "notes": payload.notes,
    }

    response = supabase_client.table("support_sessions").insert(insert_data).execute()
    row = response.data[0]

    sched_str = row["scheduled_for"]
    sched_dt = (
        datetime.fromisoformat(sched_str.replace("Z", "+00:00"))
        if sched_str
        else datetime.now()
    )

    return SupportSession(
        id=row["id"],
        expert_patient_id=row["expert_patient_id"],
        title=row["title"],
        kind=payload.kind,
        scheduled_for=sched_dt,
        capacity=row["capacity"],
        enrolled_count=row["enrolled_count"],
        notes=row.get("notes") or "",
    )


def _ensure_expert(profile: PatientProfile) -> None:
    if profile.role != AppRole.EXPERT_PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette fonctionnalité est réservée aux patients experts.",
        )


def _row_to_profile(row: dict) -> PatientProfile:
    role_str = row["role"]
    role = AppRole.EXPERT_PATIENT if role_str == "expert_patient" else AppRole.PATIENT
    return PatientProfile(
        id=row["id"],
        full_name=row["full_name"],
        role=role,
        privacy_level=row["privacy_level"],
        main_goal=row["primary_goal"],
        weekly_activity_minutes=row["weekly_activity_minutes"],
        challenge_completion_rate=row["challenge_completion_rate"],
    )
