from datetime import datetime

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.social.schemas import (
    AppRole,
    FeedPost,
    FeedPostCreate,
    PostType,
    SupportResponse,
)

FEED_TABLE = "feed_posts"
PROFILES_TABLE = "profiles"


def list_feed(limit: int = 20, offset: int = 0) -> list[FeedPost]:
    response = (
        supabase_client.table(FEED_TABLE)
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [_row_to_post(row) for row in response.data]


def create_post(payload: FeedPostCreate) -> FeedPost:
    profile = _get_profile_or_404(payload.author_id)

    insert_data = {
        "author_id": profile["id"],
        "author_name": profile["full_name"],
        "author_role": profile["role"],
        "type": payload.type.value,
        "content": payload.content,
        "achievement_label": payload.achievement_label,
        "likes": 0,
        "comments_count": 0,
    }
    response = supabase_client.table(FEED_TABLE).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de publier le statut.",
        )
    return _row_to_post(response.data[0])


def add_support(post_id: int) -> SupportResponse:
    row = _get_post_or_404(post_id)
    new_likes = int(row.get("likes") or 0) + 1
    update_response = (
        supabase_client.table(FEED_TABLE)
        .update({"likes": new_likes})
        .eq("id", post_id)
        .execute()
    )
    if not update_response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible d'ajouter le soutien.",
        )
    return SupportResponse(post_id=post_id, likes=update_response.data[0]["likes"])


def remove_support(post_id: int) -> SupportResponse:
    row = _get_post_or_404(post_id)
    new_likes = max(0, int(row.get("likes") or 0) - 1)
    update_response = (
        supabase_client.table(FEED_TABLE)
        .update({"likes": new_likes})
        .eq("id", post_id)
        .execute()
    )
    if not update_response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de retirer le soutien.",
        )
    return SupportResponse(post_id=post_id, likes=update_response.data[0]["likes"])


def _get_post_or_404(post_id: int) -> dict:
    response = supabase_client.table(FEED_TABLE).select("*").eq("id", post_id).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication introuvable.",
        )
    return response.data[0]


def _get_profile_or_404(profile_id: int) -> dict:
    response = (
        supabase_client.table(PROFILES_TABLE).select("id, full_name, role").eq("id", profile_id).execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auteur introuvable.",
        )
    return response.data[0]


def _row_to_post(row: dict) -> FeedPost:
    created_at_raw = row.get("created_at")
    created_at = (
        datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        if isinstance(created_at_raw, str)
        else created_at_raw or datetime.now()
    )
    role = (
        AppRole.EXPERT_PATIENT
        if row.get("author_role") == "expert_patient"
        else AppRole.PATIENT
    )
    post_type = (
        PostType.ACHIEVEMENT if row.get("type") == "achievement" else PostType.POST
    )
    return FeedPost(
        id=row["id"],
        author_id=row["author_id"],
        author_name=row["author_name"],
        author_role=role,
        type=post_type,
        content=row["content"],
        achievement_label=row.get("achievement_label"),
        likes=row.get("likes") or 0,
        comments_count=row.get("comments_count") or 0,
        created_at=created_at,
    )
