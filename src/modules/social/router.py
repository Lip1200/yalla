from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.security import AuthIdentity, get_current_user, get_profile_for_identity
from src.modules.social.schemas import (
    FeedComment,
    FeedCommentCreate,
    FeedPost,
    FeedPostCreate,
    Friend,
    FriendCreate,
    FriendRequest,
    FriendSuggestion,
    Group,
    GroupCategory,
    GroupCreate,
    GroupDetail,
    GroupJoinRequest,
    GroupMember,
    SupportResponse,
)
from src.modules.social.service import (
    accept_friend_request,
    add_comment,
    add_friend,
    add_support,
    create_group,
    create_post,
    get_group,
    join_group,
    leave_group,
    list_comments,
    list_feed,
    list_friend_requests,
    list_friend_suggestions,
    list_friends,
    list_groups_for_member,
    list_sent_friend_requests,
    list_groups,
    list_members,
    reject_friend_request,
    remove_friend,
    remove_support,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/feed", response_model=list[FeedPost])
def read_feed(limit: int = 20, offset: int = 0):
    return list_feed(limit=limit, offset=offset)


@router.post("/feed", response_model=FeedPost, status_code=status.HTTP_201_CREATED)
def publish_post(payload: FeedPostCreate):
    return create_post(payload)


def _resolve_supporting_user_id(
    explicit: int | None,
    identity: AuthIdentity,
) -> int:
    """Pick the user_id to record as the supporter.

    - Real user: derive from their profile (the explicit query param is
      ignored — a patient cannot "like as someone else").
    - Service token: explicit query param is required (no profile to
      derive from); typically used by demo scripts.
    """
    if not identity.is_service:
        profile = get_profile_for_identity(identity)
        if not profile or "id" not in profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aucun profil rattaché à ce compte.",
            )
        return int(profile["id"])
    if explicit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id requis pour les appels via service token.",
        )
    return explicit


@router.post("/feed/{post_id}/support", response_model=SupportResponse)
def support_post(
    post_id: int,
    user_id: int | None = Query(default=None, description="Required for service token; ignored for real users."),
    identity: AuthIdentity = Depends(get_current_user),
):
    resolved = _resolve_supporting_user_id(user_id, identity)
    return add_support(post_id, resolved)


@router.delete("/feed/{post_id}/support", response_model=SupportResponse)
def unsupport_post(
    post_id: int,
    user_id: int | None = Query(default=None, description="Required for service token; ignored for real users."),
    identity: AuthIdentity = Depends(get_current_user),
):
    resolved = _resolve_supporting_user_id(user_id, identity)
    return remove_support(post_id, resolved)


@router.get("/feed/{post_id}/comments", response_model=list[FeedComment])
def read_comments(post_id: int):
    return list_comments(post_id)


@router.post(
    "/feed/{post_id}/comments",
    response_model=FeedComment,
    status_code=status.HTTP_201_CREATED,
)
def post_comment(
    post_id: int,
    payload: FeedCommentCreate,
    user_id: int | None = Query(default=None, description="Required for service token; ignored for real users."),
    identity: AuthIdentity = Depends(get_current_user),
):
    resolved = _resolve_supporting_user_id(user_id, identity)
    return add_comment(post_id, resolved, payload)


@router.get("/groups", response_model=list[Group])
def read_groups(category: GroupCategory | None = None):
    return list_groups(category=category)


@router.post("/groups", response_model=Group, status_code=status.HTTP_201_CREATED)
def add_group(payload: GroupCreate):
    return create_group(payload)


@router.get("/groups/{group_id}", response_model=GroupDetail)
def read_group(group_id: int):
    return get_group(group_id)


@router.get("/users/{user_id}/groups", response_model=list[Group])
def read_user_groups(user_id: int):
    return list_groups_for_member(user_id)


@router.post("/groups/{group_id}/join", response_model=GroupDetail)
def join_group_route(group_id: int, payload: GroupJoinRequest):
    return join_group(group_id, payload.user_id)


@router.delete("/groups/{group_id}/members/{user_id}", response_model=GroupDetail)
def leave_group_route(group_id: int, user_id: int):
    return leave_group(group_id, user_id)


@router.get("/groups/{group_id}/members", response_model=list[GroupMember])
def read_members(group_id: int):
    return list_members(group_id)


@router.get("/suggestions/{patient_id}", response_model=list[FriendSuggestion])
def read_friend_suggestions(patient_id: int, limit: int = Query(default=10, ge=1, le=50)):
    return list_friend_suggestions(patient_id, limit=limit)


@router.get("/friends/{patient_id}", response_model=list[Friend])
def read_friends(patient_id: int):
    return list_friends(patient_id)


@router.post("/friends/{patient_id}", response_model=Friend, status_code=status.HTTP_201_CREATED)
def add_friend_route(patient_id: int, payload: FriendCreate):
    return add_friend(patient_id, payload.friend_id)


@router.delete("/friends/{patient_id}/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend_route(patient_id: int, friend_id: int):
    remove_friend(patient_id, friend_id)


@router.get("/friends/{patient_id}/requests", response_model=list[FriendRequest])
def read_friend_requests(patient_id: int):
    return list_friend_requests(patient_id)


@router.get("/friends/{patient_id}/sent", response_model=list[Friend])
def read_sent_requests(patient_id: int):
    return list_sent_friend_requests(patient_id)


@router.post(
    "/friends/{patient_id}/requests/{requester_id}/accept",
    response_model=Friend,
)
def accept_friend(patient_id: int, requester_id: int):
    return accept_friend_request(patient_id, requester_id)


@router.post(
    "/friends/{patient_id}/requests/{requester_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reject_friend(patient_id: int, requester_id: int):
    reject_friend_request(patient_id, requester_id)
