from fastapi import APIRouter, Depends, status

from src.core.security import get_current_user
from src.modules.social.schemas import (
    FeedPost,
    FeedPostCreate,
    Group,
    GroupCategory,
    GroupCreate,
    GroupDetail,
    GroupJoinRequest,
    GroupMember,
    SupportResponse,
)
from src.modules.social.service import (
    add_support,
    create_group,
    create_post,
    get_group,
    join_group,
    leave_group,
    list_feed,
    list_groups,
    list_members,
    remove_support,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/feed", response_model=list[FeedPost])
def read_feed(limit: int = 20, offset: int = 0):
    return list_feed(limit=limit, offset=offset)


@router.post("/feed", response_model=FeedPost, status_code=status.HTTP_201_CREATED)
def publish_post(payload: FeedPostCreate):
    return create_post(payload)


@router.post("/feed/{post_id}/support", response_model=SupportResponse)
def support_post(post_id: int):
    return add_support(post_id)


@router.delete("/feed/{post_id}/support", response_model=SupportResponse)
def unsupport_post(post_id: int):
    return remove_support(post_id)


@router.get("/groups", response_model=list[Group])
def read_groups(category: GroupCategory | None = None):
    return list_groups(category=category)


@router.post("/groups", response_model=Group, status_code=status.HTTP_201_CREATED)
def add_group(payload: GroupCreate):
    return create_group(payload)


@router.get("/groups/{group_id}", response_model=GroupDetail)
def read_group(group_id: int):
    return get_group(group_id)


@router.post("/groups/{group_id}/join", response_model=GroupDetail)
def join_group_route(group_id: int, payload: GroupJoinRequest):
    return join_group(group_id, payload.user_id)


@router.delete("/groups/{group_id}/members/{user_id}", response_model=GroupDetail)
def leave_group_route(group_id: int, user_id: int):
    return leave_group(group_id, user_id)


@router.get("/groups/{group_id}/members", response_model=list[GroupMember])
def read_members(group_id: int):
    return list_members(group_id)
