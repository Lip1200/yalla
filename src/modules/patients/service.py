from datetime import date, datetime, timedelta

from fastapi import HTTPException, status

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
    RestaurantRecommendation,
    SupportSession,
    SupportSessionCreate,
)


profiles: dict[int, PatientProfile] = {
    101: PatientProfile(
        id=101,
        full_name="Karim El Mansouri",
        role=AppRole.PATIENT,
        privacy_level="Partage médical complet",
        main_goal="Marcher régulièrement et stabiliser la glycémie",
        weekly_activity_minutes=145,
        challenge_completion_rate=64,
    ),
    102: PatientProfile(
        id=102,
        full_name="Amina Saidi",
        role=AppRole.EXPERT_PATIENT,
        privacy_level="Partage sélectif",
        main_goal="Accompagner le groupe et garder une activité régulière",
        weekly_activity_minutes=210,
        challenge_completion_rate=88,
    ),
}

feed_posts: list[FeedPost] = [
    FeedPost(
        id=1,
        author_id=102,
        author_name="Amina Saidi",
        author_role=AppRole.EXPERT_PATIENT,
        type=PostType.ACHIEVEMENT,
        achievement_label="Marche de groupe",
        content="Groupe marche terminé ce matin. 35 minutes à rythme doux, tout le monde a suivi.",
        likes=18,
        comments_count=5,
        created_at=datetime(2026, 4, 27, 9, 30),
    ),
    FeedPost(
        id=2,
        author_id=101,
        author_name="Karim El Mansouri",
        author_role=AppRole.PATIENT,
        type=PostType.POST,
        content="J'ai remplacé le dessert sucré par un fruit aujourd'hui. Petit pas, mais je le note.",
        likes=11,
        comments_count=3,
        created_at=datetime(2026, 4, 26, 18, 10),
    ),
]

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

restaurants: list[RestaurantRecommendation] = [
    RestaurantRecommendation(
        id=1,
        name="Maison Verte",
        area="Centre-ville",
        diabetes_friendly_score=92,
        best_for="Déjeuner léger",
        notes="Options riches en légumes, portions modulables et desserts sans sucre ajouté.",
    ),
    RestaurantRecommendation(
        id=2,
        name="Atlas Bowl",
        area="Plainpalais",
        diabetes_friendly_score=87,
        best_for="Repas rapide équilibré",
        notes="Bowls personnalisables avec céréales complètes, protéines maigres et sauces séparées.",
    ),
    RestaurantRecommendation(
        id=3,
        name="Le Jardin Simple",
        area="Eaux-Vives",
        diabetes_friendly_score=82,
        best_for="Dîner calme",
        notes="Carte claire, plats grillés, accompagnements légumes disponibles.",
    ),
]

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

sessions: list[SupportSession] = [
    SupportSession(
        id=1,
        expert_patient_id=102,
        title="Marche douce du samedi",
        kind="group",
        scheduled_for=datetime(2026, 5, 2, 9, 30),
        capacity=12,
        enrolled_count=8,
        notes="Parcours plat, prévoir bouteille d'eau.",
    ),
]


def get_profile(patient_id: int) -> PatientProfile:
    if patient_id not in profiles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    return profiles[patient_id]


def list_feed(patient_id: int) -> list[FeedPost]:
    get_profile(patient_id)
    return sorted(feed_posts, key=lambda post: post.created_at, reverse=True)


def create_post(patient_id: int, payload: FeedPostCreate) -> FeedPost:
    profile = get_profile(patient_id)
    post = FeedPost(
        id=max([item.id for item in feed_posts], default=0) + 1,
        author_id=profile.id,
        author_name=profile.full_name,
        author_role=profile.role,
        type=payload.type,
        content=payload.content,
        achievement_label=payload.achievement_label,
        likes=0,
        comments_count=0,
        created_at=datetime.now(),
    )
    feed_posts.append(post)
    return post


def get_progression(patient_id: int) -> Progression:
    profile = get_profile(patient_id)
    return Progression(
        weekly_activity_minutes=profile.weekly_activity_minutes,
        challenge_completion_rate=profile.challenge_completion_rate,
        current_streak_days=6 if profile.role == AppRole.EXPERT_PATIENT else 3,
        active_challenges=challenges.get(patient_id, []),
    )


def list_restaurants(patient_id: int) -> list[RestaurantRecommendation]:
    get_profile(patient_id)
    return restaurants


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
    profile = get_profile(patient_id)
    updated_profile = profile.model_copy(update={"privacy_level": payload.privacy_level})
    profiles[patient_id] = updated_profile
    return get_settings(patient_id)


def list_sessions(patient_id: int) -> list[SupportSession]:
    profile = get_profile(patient_id)
    _ensure_expert(profile)
    return [session for session in sessions if session.expert_patient_id == patient_id]


def create_session(patient_id: int, payload: SupportSessionCreate) -> SupportSession:
    profile = get_profile(patient_id)
    _ensure_expert(profile)

    session = SupportSession(
        id=max([item.id for item in sessions], default=0) + 1,
        expert_patient_id=patient_id,
        title=payload.title,
        kind=payload.kind,
        scheduled_for=payload.scheduled_for,
        capacity=payload.capacity,
        enrolled_count=0,
        notes=payload.notes,
    )
    sessions.append(session)
    return session


def _ensure_expert(profile: PatientProfile) -> None:
    if profile.role != AppRole.EXPERT_PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette fonctionnalité est réservée aux patients experts.",
        )
