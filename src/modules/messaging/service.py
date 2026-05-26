from datetime import datetime, timezone

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.core.security import AuthIdentity, get_profile_for_identity
from src.modules.messaging.schemas import (
    Conversation,
    ConversationKind,
    ConversationParticipantSummary,
    DirectConversationCreate,
    MarkReadResponse,
    Message,
    MessageCreate,
)

CONVERSATIONS_TABLE = "conversations"
PARTICIPANTS_TABLE = "conversation_participants"
MESSAGES_TABLE = "messages"
PROFILES_TABLE = "profiles"


def list_my_conversations(identity: AuthIdentity, user_id_override: int | None = None) -> list[Conversation]:
    caller_id = _resolve_caller_id(identity, user_id_override)

    # Conversations I'm part of.
    parts = (
        supabase_client.table(PARTICIPANTS_TABLE)
        .select("conversation_id, last_read_at")
        .eq("user_id", caller_id)
        .execute()
    )
    if not parts.data:
        return []

    conv_ids = [row["conversation_id"] for row in parts.data]
    last_read_by_conv = {row["conversation_id"]: row.get("last_read_at") for row in parts.data}

    conv_rows = (
        supabase_client.table(CONVERSATIONS_TABLE)
        .select("*")
        .in_("id", conv_ids)
        .execute()
    ).data or []

    result: list[Conversation] = []
    for row in conv_rows:
        cid = row["id"]
        result.append(
            _build_conversation_view(cid, row, caller_id, last_read_by_conv.get(cid))
        )

    # Sort newest activity first; conversations with no messages last.
    result.sort(
        key=lambda c: c.last_message_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return result


def open_direct_conversation(
    identity: AuthIdentity,
    payload: DirectConversationCreate,
    user_id_override: int | None = None,
) -> Conversation:
    caller_id = _resolve_caller_id(identity, user_id_override)
    other_id = payload.other_user_id
    if other_id == caller_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une conversation directe nécessite deux participants distincts.",
        )

    _ensure_profile_exists(other_id)

    existing = _find_direct_between(caller_id, other_id)
    if existing is not None:
        return _build_conversation_view(existing["id"], existing, caller_id, None)

    insert_resp = (
        supabase_client.table(CONVERSATIONS_TABLE)
        .insert({"kind": ConversationKind.DIRECT.value})
        .execute()
    )
    if not insert_resp.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de créer la conversation.",
        )
    conv_row = insert_resp.data[0]
    cid = conv_row["id"]
    supabase_client.table(PARTICIPANTS_TABLE).insert(
        [
            {"conversation_id": cid, "user_id": caller_id},
            {"conversation_id": cid, "user_id": other_id},
        ]
    ).execute()
    return _build_conversation_view(cid, conv_row, caller_id, None)


def get_thread(
    identity: AuthIdentity,
    conversation_id: int,
    limit: int = 50,
    user_id_override: int | None = None,
) -> list[Message]:
    caller_id = _resolve_caller_id(identity, user_id_override)
    _ensure_participant_or_403(conversation_id, caller_id)

    response = (
        supabase_client.table(MESSAGES_TABLE)
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("sent_at", desc=False)
        .limit(max(1, min(limit, 500)))
        .execute()
    )
    names = _resolve_sender_names([row["sender_id"] for row in response.data or []])
    return [
        _row_to_message(row, caller_id, names.get(row["sender_id"], "Inconnu"))
        for row in response.data or []
    ]


def send_message(
    identity: AuthIdentity,
    conversation_id: int,
    payload: MessageCreate,
    user_id_override: int | None = None,
) -> Message:
    caller_id = _resolve_caller_id(identity, user_id_override)
    _ensure_participant_or_403(conversation_id, caller_id)

    insert_resp = (
        supabase_client.table(MESSAGES_TABLE)
        .insert(
            {
                "conversation_id": conversation_id,
                "sender_id": caller_id,
                "content": payload.content,
            }
        )
        .execute()
    )
    if not insert_resp.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Envoi du message impossible.",
        )

    row = insert_resp.data[0]
    sender_name = _resolve_sender_names([caller_id]).get(caller_id, "Vous")

    # Bump the sender's last_read_at so their own message isn't counted unread.
    supabase_client.table(PARTICIPANTS_TABLE).update(
        {"last_read_at": _now_iso()}
    ).eq("conversation_id", conversation_id).eq("user_id", caller_id).execute()

    return _row_to_message(row, caller_id, sender_name)


def mark_read(
    identity: AuthIdentity,
    conversation_id: int,
    user_id_override: int | None = None,
) -> MarkReadResponse:
    caller_id = _resolve_caller_id(identity, user_id_override)
    _ensure_participant_or_403(conversation_id, caller_id)
    now = datetime.now(timezone.utc)
    supabase_client.table(PARTICIPANTS_TABLE).update({"last_read_at": now.isoformat()}).eq(
        "conversation_id", conversation_id
    ).eq("user_id", caller_id).execute()
    return MarkReadResponse(conversation_id=conversation_id, last_read_at=now)


# ===========================================================================
# Helpers
# ===========================================================================


def _resolve_caller_id(identity: AuthIdentity, override: int | None) -> int:
    if identity.is_service:
        if override is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id requis pour les appels via service token.",
            )
        return override
    profile = get_profile_for_identity(identity)
    if not profile or "id" not in profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun profil rattaché à ce compte.",
        )
    return int(profile["id"])


def _ensure_profile_exists(profile_id: int) -> None:
    response = (
        supabase_client.table(PROFILES_TABLE).select("id").eq("id", profile_id).limit(1).execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destinataire introuvable.",
        )


def _ensure_participant_or_403(conversation_id: int, user_id: int) -> None:
    # Service token bypasses participation checks — it's an admin path.
    response = (
        supabase_client.table(PARTICIPANTS_TABLE)
        .select("conversation_id")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas participant à cette conversation.",
        )


def _find_direct_between(user_a: int, user_b: int) -> dict | None:
    """Find the existing direct conversation between two users (order-
    insensitive). Returns the conversation row or None."""
    parts_a = (
        supabase_client.table(PARTICIPANTS_TABLE)
        .select("conversation_id")
        .eq("user_id", user_a)
        .execute()
    )
    if not parts_a.data:
        return None
    a_convs = {row["conversation_id"] for row in parts_a.data}

    parts_b = (
        supabase_client.table(PARTICIPANTS_TABLE)
        .select("conversation_id")
        .eq("user_id", user_b)
        .execute()
    )
    common = a_convs.intersection({row["conversation_id"] for row in parts_b.data or []})
    if not common:
        return None

    conv_rows = (
        supabase_client.table(CONVERSATIONS_TABLE)
        .select("*")
        .in_("id", list(common))
        .eq("kind", ConversationKind.DIRECT.value)
        .execute()
    )
    return conv_rows.data[0] if conv_rows.data else None


def _build_conversation_view(
    conversation_id: int,
    conv_row: dict,
    caller_id: int,
    last_read_at: str | None,
) -> Conversation:
    participants = _list_participants(conversation_id)
    last_message_row = _latest_message(conversation_id)
    unread = _count_unread(conversation_id, caller_id, last_read_at)
    return Conversation(
        id=conversation_id,
        kind=ConversationKind(conv_row.get("kind") or "direct"),
        title=conv_row.get("title"),
        participants=participants,
        last_message_preview=(last_message_row.get("content") if last_message_row else None),
        last_message_at=_parse_dt(last_message_row.get("sent_at")) if last_message_row else None,
        unread_count=unread,
    )


def _list_participants(conversation_id: int) -> list[ConversationParticipantSummary]:
    parts = (
        supabase_client.table(PARTICIPANTS_TABLE)
        .select("user_id")
        .eq("conversation_id", conversation_id)
        .execute()
    ).data or []
    if not parts:
        return []
    user_ids = [row["user_id"] for row in parts]
    profiles = (
        supabase_client.table(PROFILES_TABLE)
        .select("id, full_name, role")
        .in_("id", user_ids)
        .execute()
    ).data or []
    by_id = {row["id"]: row for row in profiles}
    return [
        ConversationParticipantSummary(
            user_id=uid,
            full_name=by_id.get(uid, {}).get("full_name") or "Inconnu",
            role=by_id.get(uid, {}).get("role") or "patient",
        )
        for uid in user_ids
    ]


def _latest_message(conversation_id: int) -> dict | None:
    response = (
        supabase_client.table(MESSAGES_TABLE)
        .select("content, sent_at")
        .eq("conversation_id", conversation_id)
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def _count_unread(conversation_id: int, caller_id: int, last_read_at: str | None) -> int:
    query = (
        supabase_client.table(MESSAGES_TABLE)
        .select("id", count="exact")
        .eq("conversation_id", conversation_id)
        .neq("sender_id", caller_id)
    )
    if last_read_at:
        query = query.gt("sent_at", last_read_at)
    response = query.execute()
    return response.count or 0


def _resolve_sender_names(user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    profiles = (
        supabase_client.table(PROFILES_TABLE)
        .select("id, full_name")
        .in_("id", list(set(user_ids)))
        .execute()
    ).data or []
    return {row["id"]: row.get("full_name") or "Inconnu" for row in profiles}


def _row_to_message(row: dict, caller_id: int, sender_name: str) -> Message:
    sent = _parse_dt(row.get("sent_at")) or datetime.now(timezone.utc)
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        sender_id=row["sender_id"],
        sender_name=sender_name,
        content=row["content"],
        sent_at=sent,
        is_mine=row["sender_id"] == caller_id,
    )


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
