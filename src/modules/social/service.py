from datetime import datetime

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.social.schemas import (
    AppRole,
    FeedPost,
    FeedPostCreate,
    Friend,
    FriendRequest,
    FriendSuggestion,
    Group,
    GroupCategory,
    GroupCreate,
    GroupDetail,
    GroupMember,
    GroupMemberRole,
    PostType,
    SupportResponse,
)

FEED_TABLE = "feed_posts"
FEED_SUPPORTS_TABLE = "feed_post_supports"
PROFILES_TABLE = "profiles"
GROUPS_TABLE = "groups"
GROUP_MEMBERS_TABLE = "group_members"


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


def add_support(post_id: int, user_id: int) -> SupportResponse:
    """Record that `user_id` supports `post_id`. Idempotent — re-supporting
    is a no-op (the underlying composite primary key rejects duplicates;
    we swallow the error and just return the current count)."""
    _get_post_or_404(post_id)
    _get_profile_or_404(user_id)

    try:
        supabase_client.table(FEED_SUPPORTS_TABLE).insert(
            {"post_id": post_id, "user_id": user_id}
        ).execute()
    except Exception:
        # Duplicate (post_id, user_id) — primary key violation. Idempotent
        # behaviour: report the current count without raising.
        pass

    return _refresh_likes_count(post_id)


def remove_support(post_id: int, user_id: int) -> SupportResponse:
    """Drop the support row for (post_id, user_id). No-op if there isn't one."""
    _get_post_or_404(post_id)

    supabase_client.table(FEED_SUPPORTS_TABLE).delete().eq(
        "post_id", post_id
    ).eq("user_id", user_id).execute()

    return _refresh_likes_count(post_id)


def _refresh_likes_count(post_id: int) -> SupportResponse:
    """Recompute likes from feed_post_supports and update the denormalized
    `feed_posts.likes` counter so the feed listing reads stay fast."""
    count_resp = (
        supabase_client.table(FEED_SUPPORTS_TABLE)
        .select("post_id", count="exact")
        .eq("post_id", post_id)
        .execute()
    )
    new_likes = count_resp.count or 0
    supabase_client.table(FEED_TABLE).update({"likes": new_likes}).eq(
        "id", post_id
    ).execute()
    return SupportResponse(post_id=post_id, likes=new_likes)


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


def list_groups(category: GroupCategory | None = None) -> list[Group]:
    query = supabase_client.table(GROUPS_TABLE).select("*").order("created_at", desc=True)
    if category is not None:
        query = query.eq("category", category.value)
    response = query.execute()
    return [_row_to_group(row) for row in response.data]


def list_groups_for_member(user_id: int) -> list[Group]:
    """Return groups the patient is a member of (either admin or member)."""
    memberships = (
        supabase_client.table(GROUP_MEMBERS_TABLE)
        .select("group_id")
        .eq("user_id", user_id)
        .execute()
    )
    group_ids = [row["group_id"] for row in (memberships.data or [])]
    if not group_ids:
        return []
    response = (
        supabase_client.table(GROUPS_TABLE)
        .select("*")
        .in_("id", group_ids)
        .order("created_at", desc=True)
        .execute()
    )
    return [_row_to_group(row) for row in (response.data or [])]


def create_group(payload: GroupCreate) -> Group:
    creator = _get_profile_or_404(payload.creator_id)
    insert_data = {
        "name": payload.name,
        "description": payload.description,
        "category": payload.category.value,
        "creator_id": creator["id"],
    }
    response = supabase_client.table(GROUPS_TABLE).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de créer le groupe.",
        )
    group_row = response.data[0]

    supabase_client.table(GROUP_MEMBERS_TABLE).insert(
        {
            "group_id": group_row["id"],
            "user_id": creator["id"],
            "role": GroupMemberRole.ADMIN.value,
        }
    ).execute()

    return _row_to_group(group_row)


def get_group(group_id: int) -> GroupDetail:
    row = _get_group_or_404(group_id)
    members = _list_members(group_id)
    base = _row_to_group(row, member_count_override=len(members))
    return GroupDetail(**base.model_dump(), members=members)


def join_group(group_id: int, user_id: int) -> GroupDetail:
    _get_group_or_404(group_id)
    _get_profile_or_404(user_id)

    existing = (
        supabase_client.table(GROUP_MEMBERS_TABLE)
        .select("group_id")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vous êtes déjà membre de ce groupe.",
        )

    supabase_client.table(GROUP_MEMBERS_TABLE).insert(
        {
            "group_id": group_id,
            "user_id": user_id,
            "role": GroupMemberRole.MEMBER.value,
        }
    ).execute()
    return get_group(group_id)


def leave_group(group_id: int, user_id: int) -> GroupDetail:
    group_row = _get_group_or_404(group_id)
    if group_row["creator_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le créateur ne peut pas quitter son propre groupe.",
        )

    delete_resp = (
        supabase_client.table(GROUP_MEMBERS_TABLE)
        .delete()
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not delete_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vous n'êtes pas membre de ce groupe.",
        )
    return get_group(group_id)


def list_members(group_id: int) -> list[GroupMember]:
    _get_group_or_404(group_id)
    return _list_members(group_id)


def _list_members(group_id: int) -> list[GroupMember]:
    response = (
        supabase_client.table(GROUP_MEMBERS_TABLE)
        .select("user_id, role, joined_at")
        .eq("group_id", group_id)
        .order("joined_at", desc=False)
        .execute()
    )
    members: list[GroupMember] = []
    for row in response.data:
        profile = (
            supabase_client.table(PROFILES_TABLE)
            .select("full_name")
            .eq("id", row["user_id"])
            .execute()
        )
        name = profile.data[0]["full_name"] if profile.data else "Inconnu"
        joined_raw = row["joined_at"]
        joined_at = (
            datetime.fromisoformat(joined_raw.replace("Z", "+00:00"))
            if isinstance(joined_raw, str)
            else joined_raw or datetime.now()
        )
        role = (
            GroupMemberRole.ADMIN
            if row.get("role") == GroupMemberRole.ADMIN.value
            else GroupMemberRole.MEMBER
        )
        members.append(
            GroupMember(user_id=row["user_id"], full_name=name, role=role, joined_at=joined_at)
        )
    return members


def _get_group_or_404(group_id: int) -> dict:
    response = supabase_client.table(GROUPS_TABLE).select("*").eq("id", group_id).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Groupe introuvable.",
        )
    return response.data[0]


def _row_to_group(row: dict, member_count_override: int | None = None) -> Group:
    created_raw = row.get("created_at")
    created_at = (
        datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        if isinstance(created_raw, str)
        else created_raw or datetime.now()
    )

    try:
        category = GroupCategory(row.get("category") or GroupCategory.GENERAL.value)
    except ValueError:
        category = GroupCategory.GENERAL

    creator_profile = (
        supabase_client.table(PROFILES_TABLE)
        .select("full_name")
        .eq("id", row["creator_id"])
        .execute()
    )
    creator_name = creator_profile.data[0]["full_name"] if creator_profile.data else "Inconnu"

    if member_count_override is None:
        members_resp = (
            supabase_client.table(GROUP_MEMBERS_TABLE)
            .select("user_id", count="exact")
            .eq("group_id", row["id"])
            .execute()
        )
        member_count = members_resp.count or len(members_resp.data or [])
    else:
        member_count = member_count_override

    return Group(
        id=row["id"],
        name=row["name"],
        description=row.get("description") or "",
        category=category,
        creator_id=row["creator_id"],
        creator_name=creator_name,
        member_count=member_count,
        created_at=created_at,
    )


def list_friend_suggestions(
    requester_id: int, limit: int = 10
) -> list[FriendSuggestion]:
    """Return other patient / expert_patient profiles the requester could add.
    Excludes the requester themself, doctors, and anyone already linked
    via patient_friends in either direction (pending or accepted)."""
    linked_out = (
        supabase_client.table(FRIENDS_TABLE)
        .select("friend_id")
        .eq("patient_id", requester_id)
        .execute()
    )
    linked_in = (
        supabase_client.table(FRIENDS_TABLE)
        .select("patient_id")
        .eq("friend_id", requester_id)
        .execute()
    )
    excluded_ids = {requester_id}
    for row in linked_out.data or []:
        excluded_ids.add(row["friend_id"])
    for row in linked_in.data or []:
        excluded_ids.add(row["patient_id"])

    query = (
        supabase_client.table(PROFILES_TABLE)
        .select("id, full_name, role, primary_goal, status")
        .in_("role", ["patient", "expert_patient"])
        .order("id")
        .limit(limit + len(excluded_ids))  # over-fetch so filtering below still hits `limit`
    )
    response = query.execute()
    suggestions: list[FriendSuggestion] = []
    for row in response.data or []:
        if row["id"] in excluded_ids:
            continue
        if len(suggestions) >= limit:
            break
        role_value = row.get("role") or "patient"
        try:
            role = AppRole(role_value)
        except ValueError:
            role = AppRole.PATIENT
        detail = (row.get("primary_goal") or row.get("status") or "").strip()
        if not detail:
            detail = "Patient Yalla" if role == AppRole.PATIENT else "Patient expert"
        suggestions.append(
            FriendSuggestion(
                id=row["id"],
                name=row.get("full_name") or "Profil Yalla",
                detail=detail,
                role=role,
            )
        )
    return suggestions


FRIENDS_TABLE = "patient_friends"


def _parse_created_at(value) -> datetime:
    return (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, str)
        else value or datetime.now()
    )


def _role_from_raw(raw) -> AppRole:
    try:
        return AppRole(raw or "patient")
    except ValueError:
        return AppRole.PATIENT


def list_friends(patient_id: int) -> list[Friend]:
    """Return profiles accepted as friends by the patient, looking in both
    directions (rows where patient is requester OR receiver, status='accepted').
    Sorted by most recently linked first."""
    _get_profile_or_404(patient_id)
    rows_out = (
        supabase_client.table(FRIENDS_TABLE)
        .select("friend_id, created_at")
        .eq("patient_id", patient_id)
        .eq("status", "accepted")
        .execute()
    )
    rows_in = (
        supabase_client.table(FRIENDS_TABLE)
        .select("patient_id, created_at")
        .eq("friend_id", patient_id)
        .eq("status", "accepted")
        .execute()
    )
    pairs: list[tuple[int, str | None]] = []
    for row in rows_out.data or []:
        pairs.append((row["friend_id"], row.get("created_at")))
    for row in rows_in.data or []:
        pairs.append((row["patient_id"], row.get("created_at")))
    if not pairs:
        return []

    pairs.sort(key=lambda p: p[1] or "", reverse=True)
    ids = sorted({pair[0] for pair in pairs})
    profiles_resp = (
        supabase_client.table(PROFILES_TABLE)
        .select("id, full_name, role, primary_goal")
        .in_("id", ids)
        .execute()
    )
    profiles = {row["id"]: row for row in (profiles_resp.data or [])}

    result: list[Friend] = []
    seen: set[int] = set()
    for friend_id, created_raw in pairs:
        if friend_id in seen:
            continue
        seen.add(friend_id)
        profile = profiles.get(friend_id)
        if profile is None:
            continue
        result.append(
            Friend(
                id=profile["id"],
                name=profile.get("full_name") or "Profil Yalla",
                role=_role_from_raw(profile.get("role")),
                primary_goal=profile.get("primary_goal") or "",
                created_at=_parse_created_at(created_raw),
                status="accepted",
            )
        )
    return result


def list_sent_friend_requests(patient_id: int) -> list[Friend]:
    """Pending requests `patient_id` has SENT but the receiver hasn't
    accepted yet. Used by the patient-app to show 'Demande envoyée'
    status and let the user cancel if they want."""
    _get_profile_or_404(patient_id)
    rows = (
        supabase_client.table(FRIENDS_TABLE)
        .select("friend_id, created_at")
        .eq("patient_id", patient_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
    )
    friend_ids = [row["friend_id"] for row in (rows.data or [])]
    if not friend_ids:
        return []
    profiles_resp = (
        supabase_client.table(PROFILES_TABLE)
        .select("id, full_name, role, primary_goal")
        .in_("id", friend_ids)
        .execute()
    )
    profiles = {row["id"]: row for row in (profiles_resp.data or [])}
    result: list[Friend] = []
    for row in rows.data or []:
        profile = profiles.get(row["friend_id"])
        if profile is None:
            continue
        result.append(
            Friend(
                id=profile["id"],
                name=profile.get("full_name") or "Profil Yalla",
                role=_role_from_raw(profile.get("role")),
                primary_goal=profile.get("primary_goal") or "",
                created_at=_parse_created_at(row.get("created_at")),
                status="pending",
            )
        )
    return result


def list_friend_requests(patient_id: int) -> list[FriendRequest]:
    """Pending requests that `patient_id` has received and hasn't yet
    accepted or rejected. Used by the patient-app to render the
    'Demandes reçues' section."""
    _get_profile_or_404(patient_id)
    rows = (
        supabase_client.table(FRIENDS_TABLE)
        .select("patient_id, created_at")
        .eq("friend_id", patient_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
    )
    requester_ids = [row["patient_id"] for row in (rows.data or [])]
    if not requester_ids:
        return []

    profiles_resp = (
        supabase_client.table(PROFILES_TABLE)
        .select("id, full_name, role, primary_goal")
        .in_("id", requester_ids)
        .execute()
    )
    profiles = {row["id"]: row for row in (profiles_resp.data or [])}

    result: list[FriendRequest] = []
    for row in rows.data or []:
        profile = profiles.get(row["patient_id"])
        if profile is None:
            continue
        result.append(
            FriendRequest(
                requester_id=profile["id"],
                requester_name=profile.get("full_name") or "Profil Yalla",
                requester_role=_role_from_raw(profile.get("role")),
                primary_goal=profile.get("primary_goal") or "",
                created_at=_parse_created_at(row.get("created_at")),
            )
        )
    return result


def add_friend(patient_id: int, friend_id: int) -> Friend:
    """Send a friend request. Creates a row (patient_id → friend_id) with
    status='pending'. Idempotent — returns the existing row's status if
    one already exists in either direction (so the requester sees the
    same state as the friend list)."""
    if patient_id == friend_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="On ne peut pas s'ajouter soi-même.",
        )
    _get_profile_or_404(patient_id)
    friend_profile = _get_profile_or_404(friend_id)

    existing = (
        supabase_client.table(FRIENDS_TABLE)
        .select("status, created_at")
        .eq("patient_id", patient_id)
        .eq("friend_id", friend_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        row = existing.data[0]
    else:
        reverse = (
            supabase_client.table(FRIENDS_TABLE)
            .select("status, created_at")
            .eq("patient_id", friend_id)
            .eq("friend_id", patient_id)
            .limit(1)
            .execute()
        )
        if reverse.data:
            row = reverse.data[0]
        else:
            inserted = (
                supabase_client.table(FRIENDS_TABLE)
                .insert(
                    {"patient_id": patient_id, "friend_id": friend_id, "status": "pending"}
                )
                .execute()
            )
            row = inserted.data[0] if inserted.data else {"status": "pending"}

    return Friend(
        id=friend_profile["id"],
        name=friend_profile.get("full_name") or "Profil Yalla",
        role=_role_from_raw(friend_profile.get("role")),
        primary_goal=friend_profile.get("primary_goal") or "",
        created_at=_parse_created_at(row.get("created_at")),
        status=row.get("status") or "pending",
    )


def accept_friend_request(receiver_id: int, requester_id: int) -> Friend:
    """Accept the pending request requester_id → receiver_id. The row's
    status flips to 'accepted'. Both sides will then see each other in
    list_friends."""
    _get_profile_or_404(receiver_id)
    requester_profile = _get_profile_or_404(requester_id)

    response = (
        supabase_client.table(FRIENDS_TABLE)
        .update({"status": "accepted"})
        .eq("patient_id", requester_id)
        .eq("friend_id", receiver_id)
        .eq("status", "pending")
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande d'amitié introuvable.",
        )
    return Friend(
        id=requester_profile["id"],
        name=requester_profile.get("full_name") or "Profil Yalla",
        role=_role_from_raw(requester_profile.get("role")),
        primary_goal=requester_profile.get("primary_goal") or "",
        created_at=_parse_created_at(response.data[0].get("created_at")),
        status="accepted",
    )


def reject_friend_request(receiver_id: int, requester_id: int) -> None:
    """Reject the pending request — deletes the row so the requester can
    re-try later. No-op if no pending row exists."""
    _get_profile_or_404(receiver_id)
    supabase_client.table(FRIENDS_TABLE).delete().eq(
        "patient_id", requester_id
    ).eq("friend_id", receiver_id).eq("status", "pending").execute()


def remove_friend(patient_id: int, friend_id: int) -> None:
    """Drop the friendship row in either direction. No-op if neither
    exists. Use for both 'cancel pending request' and 'unfriend'."""
    _get_profile_or_404(patient_id)
    supabase_client.table(FRIENDS_TABLE).delete().eq(
        "patient_id", patient_id
    ).eq("friend_id", friend_id).execute()
    supabase_client.table(FRIENDS_TABLE).delete().eq(
        "patient_id", friend_id
    ).eq("friend_id", patient_id).execute()
