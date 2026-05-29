import base64
import uuid
from datetime import date, datetime

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.patients.schemas import (
    AccessFlagsUpdate,
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

        content = row["content"]
        image_url = row.get("image_url")
        # Fallback intelligent si la colonne image_url n'existe pas en BDD
        if not image_url and content and " ||image||" in content:
            parts = content.split(" ||image||", 1)
            content = parts[0]
            image_url = parts[1]

        posts.append(
            FeedPost(
                id=row["id"],
                author_id=row["author_id"],
                author_name=row["author_name"],
                author_role=role,
                type=post_type,
                content=content,
                image_url=image_url,
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

    image_url = None
    if payload.image_base64:
        # New path: upload to Supabase Storage and store only the URL in
        # `image_url`. Falls back to the legacy "base64 in column" or
        # "base64 in content via ||image|| separator" behavior if the
        # Storage upload fails (missing bucket, RLS denial, etc.) so
        # the post still goes through.
        try:
            image_url = _upload_feed_image_to_storage(payload.image_base64)
            insert_data["image_url"] = image_url
        except Exception:
            image_url = payload.image_base64
            insert_data["image_url"] = payload.image_base64

    try:
        response = supabase_client.table("feed_posts").insert(insert_data).execute()
    except Exception as e:
        err_msg = str(e)
        if "image_url" in err_msg or "PGRST204" in err_msg:
            # Fallback intelligent sans modification de BDD : on stocke l'image dans le champ content
            if payload.image_base64:
                insert_data["content"] = f"{payload.content} ||image||{payload.image_base64}"
            if "image_url" in insert_data:
                del insert_data["image_url"]
            response = supabase_client.table("feed_posts").insert(insert_data).execute()
        else:
            raise e

    row = response.data[0]
    created_at_str = row["created_at"]
    created_at_dt = (
        datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        if created_at_str
        else datetime.now()
    )

    resp_content = row["content"]
    resp_image_url = row.get("image_url")
    if not resp_image_url and resp_content and " ||image||" in resp_content:
        parts = resp_content.split(" ||image||", 1)
        resp_content = parts[0]
        resp_image_url = parts[1]

    role = AppRole.EXPERT_PATIENT if row["author_role"] == "expert_patient" else AppRole.PATIENT
    post_type = PostType.ACHIEVEMENT if row["type"] == "achievement" else PostType.POST

    return FeedPost(
        id=row["id"],
        author_id=row["author_id"],
        author_name=row["author_name"],
        author_role=role,
        type=post_type,
        content=resp_content,
        image_url=resp_image_url,
        achievement_label=row.get("achievement_label"),
        likes=row["likes"],
        comments_count=row["comments_count"],
        created_at=created_at_dt,
    )


def _fetch_active_challenges_for_patient(patient_id: int) -> list[Challenge]:
    """Read active rows from patient_challenges + join with the challenges
    template to build the legacy Challenge shape (id, title, description,
    category, progress, due_on) expected by the patient-app.

    Falls back to the seeded in-memory dict when the DB has no row — the
    demo patients (101 Karim, 102 Amina) keep their fake-but-pretty data
    so the dashboards remain populated for the class demo."""
    assignments = (
        supabase_client.table("patient_challenges")
        .select("id, challenge_id, progress, due_on")
        .eq("patient_id", patient_id)
        .eq("status", "active")
        .order("started_at", desc=True)
        .execute()
    )
    rows = assignments.data or []
    if not rows:
        return challenges.get(patient_id, [])

    template_ids = sorted({row["challenge_id"] for row in rows})
    templates_resp = (
        supabase_client.table("challenges")
        .select("id, title, description, category")
        .in_("id", template_ids)
        .execute()
    )
    templates = {row["id"]: row for row in (templates_resp.data or [])}

    result: list[Challenge] = []
    for row in rows:
        template = templates.get(row["challenge_id"])
        if template is None:
            continue
        due = row["due_on"]
        due_date = date.fromisoformat(due) if isinstance(due, str) else due
        result.append(
            Challenge(
                id=row["id"],
                title=template["title"],
                description=template.get("description") or "",
                category=str(template.get("category") or ""),
                progress=int(row.get("progress") or 0),
                due_on=due_date,
            )
        )
    return result


def get_progression(patient_id: int) -> Progression:
    profile = get_profile(patient_id)
    return Progression(
        weekly_activity_minutes=profile.weekly_activity_minutes,
        challenge_completion_rate=profile.challenge_completion_rate,
        current_streak_days=6 if profile.role == AppRole.EXPERT_PATIENT else 3,
        active_challenges=_fetch_active_challenges_for_patient(patient_id),
    )





def _fetch_conversations_for_patient(patient_id: int) -> list[Conversation]:
    """Read the patient's conversations from the messaging tables (migration
    011): conversation_participants → conversations → messages.

    Returns a list of `Conversation` summaries (one per conv the patient
    is in), with the OTHER participant's name as `contact_name`, the most
    recent message body as `last_message`, and the count of messages
    posted after the patient's `last_read_at` as `unread_count`.

    Falls back to the seeded in-memory `conversations` dict when the DB
    has no row — keeps demo patients (101, 102) populated for the class
    presentation. Same pattern as `_fetch_active_challenges_for_patient`."""
    parts = (
        supabase_client.table("conversation_participants")
        .select("conversation_id, last_read_at")
        .eq("user_id", patient_id)
        .execute()
    )
    rows = parts.data or []
    if not rows:
        return list(conversations.get(patient_id, []))

    conv_ids = [row["conversation_id"] for row in rows]
    last_read_by_conv: dict[int, str | None] = {
        row["conversation_id"]: row.get("last_read_at") for row in rows
    }

    other_parts = (
        supabase_client.table("conversation_participants")
        .select("conversation_id, user_id")
        .in_("conversation_id", conv_ids)
        .neq("user_id", patient_id)
        .execute()
    )
    contact_ids_by_conv: dict[int, list[int]] = {}
    for row in other_parts.data or []:
        contact_ids_by_conv.setdefault(row["conversation_id"], []).append(row["user_id"])

    all_contact_ids = sorted({uid for ids in contact_ids_by_conv.values() for uid in ids})
    contacts = {}
    if all_contact_ids:
        profile_rows = (
            supabase_client.table("profiles")
            .select("id, full_name, role")
            .in_("id", all_contact_ids)
            .execute()
        )
        contacts = {row["id"]: row for row in (profile_rows.data or [])}

    messages_resp = (
        supabase_client.table("messages")
        .select("conversation_id, sender_id, content, sent_at")
        .in_("conversation_id", conv_ids)
        .order("sent_at", desc=True)
        .execute()
    )
    latest_by_conv: dict[int, dict] = {}
    unread_by_conv: dict[int, int] = {cid: 0 for cid in conv_ids}
    for msg in messages_resp.data or []:
        cid = msg["conversation_id"]
        if cid not in latest_by_conv:
            latest_by_conv[cid] = msg
        # Own messages don't count as unread.
        if msg.get("sender_id") == patient_id:
            continue
        last_read = last_read_by_conv.get(cid)
        sent_at_raw = msg.get("sent_at")
        if last_read and isinstance(sent_at_raw, str) and sent_at_raw <= last_read:
            continue
        unread_by_conv[cid] = unread_by_conv.get(cid, 0) + 1

    results: list[Conversation] = []
    for cid in conv_ids:
        latest = latest_by_conv.get(cid)
        contact_ids = contact_ids_by_conv.get(cid, [])
        contact = contacts.get(contact_ids[0]) if contact_ids else None
        contact_name = (contact or {}).get("full_name") or "Yalla"
        raw_role = (contact or {}).get("role")
        contact_role = AppRole.EXPERT_PATIENT if raw_role == "expert_patient" else AppRole.PATIENT

        if latest is None:
            continue  # empty conversation, skip
        updated_at_raw = latest.get("sent_at")
        updated_at = (
            datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
            if isinstance(updated_at_raw, str)
            else updated_at_raw or datetime.now()
        )
        results.append(
            Conversation(
                id=cid,
                contact_name=contact_name,
                contact_role=contact_role,
                last_message=latest.get("content") or "",
                unread_count=unread_by_conv.get(cid, 0),
                updated_at=updated_at,
            )
        )

    results.sort(key=lambda c: c.updated_at, reverse=True)
    return results


def list_conversations(patient_id: int) -> list[Conversation]:
    get_profile(patient_id)
    return _fetch_conversations_for_patient(patient_id)


def start_direct_conversation(patient_id: int, friend_id: int) -> Conversation:
    """Open (or reopen) a direct 1-1 conversation between patient_id and
    friend_id. Idempotent — if a conversation already exists with both as
    participants, returns it instead of creating a duplicate."""
    if patient_id == friend_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="On ne peut pas démarrer une conversation avec soi-même.",
        )
    get_profile(patient_id)
    friend_profile = get_profile(friend_id)

    # Find conversations the patient is already in + cross-check the friend
    # is also a participant. Cheaper than a join: two filtered selects.
    my_parts = (
        supabase_client.table("conversation_participants")
        .select("conversation_id")
        .eq("user_id", patient_id)
        .execute()
    )
    my_conv_ids = [row["conversation_id"] for row in (my_parts.data or [])]
    if my_conv_ids:
        friend_parts = (
            supabase_client.table("conversation_participants")
            .select("conversation_id")
            .eq("user_id", friend_id)
            .in_("conversation_id", my_conv_ids)
            .execute()
        )
        if friend_parts.data:
            # First match is fine for direct conversations (group convs are
            # named via `title`; we don't dedupe those here).
            existing_id = friend_parts.data[0]["conversation_id"]
            existing = _fetch_conversations_for_patient(patient_id)
            for conv in existing:
                if conv.id == existing_id:
                    return conv

    # No existing direct conv — create one.
    conv_row = (
        supabase_client.table("conversations")
        .insert({"kind": "direct", "title": None})
        .execute()
        .data[0]
    )
    conversation_id = conv_row["id"]
    supabase_client.table("conversation_participants").insert(
        [
            {"conversation_id": conversation_id, "user_id": patient_id},
            {"conversation_id": conversation_id, "user_id": friend_id},
        ]
    ).execute()

    raw_role = friend_profile.role.value if hasattr(friend_profile.role, "value") else str(friend_profile.role)
    contact_role = AppRole.EXPERT_PATIENT if raw_role == "expert_patient" else AppRole.PATIENT
    return Conversation(
        id=conversation_id,
        contact_name=friend_profile.full_name,
        contact_role=contact_role,
        last_message="",
        unread_count=0,
        updated_at=datetime.now(),
    )


def get_settings(patient_id: int) -> PatientSettings:
    profile = get_profile(patient_id)
    # Read the persisted flags directly from the profiles row. Migration 016
    # added these as NOT NULL booleans with default TRUE, so any patient
    # that pre-dates the migration shows up as fully sharing — same as the
    # legacy derived behaviour.
    row = (
        supabase_client.table("profiles")
        .select(
            "share_activity, share_challenges, share_restaurants, "
            "share_posts, share_messages_with_expert"
        )
        .eq("id", patient_id)
        .limit(1)
        .execute()
        .data
    )
    flags = row[0] if row else {}
    return PatientSettings(
        profile=profile,
        share_activity=bool(flags.get("share_activity", True)),
        share_challenges=bool(flags.get("share_challenges", True)),
        share_restaurants=bool(flags.get("share_restaurants", True)),
        share_posts=bool(flags.get("share_posts", True)),
        share_messages_with_expert=bool(flags.get("share_messages_with_expert", True)),
    )


def update_privacy(patient_id: int, payload: PrivacySettingsUpdate) -> PatientSettings:
    get_profile(patient_id)
    supabase_client.table("profiles").update({"privacy_level": payload.privacy_level}).eq("id", patient_id).execute()
    return get_settings(patient_id)


def update_access_flags(patient_id: int, payload: AccessFlagsUpdate) -> PatientSettings:
    """Patch one or more share_* flags. Fields left None on the payload
    are not modified."""
    get_profile(patient_id)
    changes = payload.model_dump(exclude_none=True)
    if changes:
        supabase_client.table("profiles").update(changes).eq("id", patient_id).execute()
    return get_settings(patient_id)


def list_sessions(patient_id: int) -> list[SupportSession]:
    profile = get_profile(patient_id)

    response = (
        supabase_client.table("support_sessions")
        .select("*")
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


def join_session(patient_id: int, session_id: int) -> SupportSession:
    get_profile(patient_id)

    response = supabase_client.table("support_sessions").select("*").eq("id", session_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Séance introuvable.")

    row = response.data[0]
    if row["enrolled_count"] >= row["capacity"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La séance est déjà complète.")

    new_count = row["enrolled_count"] + 1
    update_resp = (
        supabase_client.table("support_sessions")
        .update({"enrolled_count": new_count})
        .eq("id", session_id)
        .execute()
    )

    updated_row = update_resp.data[0]
    sched_str = updated_row["scheduled_for"]
    sched_dt = (
        datetime.fromisoformat(sched_str.replace("Z", "+00:00"))
        if sched_str
        else datetime.now()
    )
    kind = SessionKind.GROUP if updated_row["kind"] == "group" else SessionKind.INDIVIDUAL

    return SupportSession(
        id=updated_row["id"],
        expert_patient_id=updated_row["expert_patient_id"],
        title=updated_row["title"],
        kind=kind,
        scheduled_for=sched_dt,
        capacity=updated_row["capacity"],
        enrolled_count=updated_row["enrolled_count"],
        notes=updated_row.get("notes") or "",
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


FEED_IMAGES_BUCKET = "feed-images"

_MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _decode_data_url(value: str) -> tuple[bytes, str, str]:
    """Accept either a raw base64 string or a `data:<mime>;base64,<payload>`
    data URL. Returns (binary, file_extension, content_type)."""
    if value.startswith("data:"):
        header, _, payload = value.partition(",")
        # header e.g. "data:image/jpeg;base64"
        mime = header.split(":", 1)[1].split(";", 1)[0].lower() or "image/jpeg"
    else:
        payload = value
        mime = "image/jpeg"
    extension = _MIME_TO_EXT.get(mime, "jpg")
    return base64.b64decode(payload), extension, mime


def _upload_feed_image_to_storage(image_base64: str) -> str:
    """Decode a base64-encoded image (raw or data URL) and upload it to
    the `feed-images` Supabase Storage bucket. Returns the public URL.

    Raises on failure — the caller is expected to catch and fall back to
    the legacy in-column or in-content storage to keep posts going through.
    """
    binary, extension, content_type = _decode_data_url(image_base64)
    filename = f"{uuid.uuid4().hex}.{extension}"
    supabase_client.storage.from_(FEED_IMAGES_BUCKET).upload(
        path=filename,
        file=binary,
        file_options={"content-type": content_type, "upsert": "false"},
    )
    return supabase_client.storage.from_(FEED_IMAGES_BUCKET).get_public_url(filename)
