from fastapi import APIRouter, Depends, status

from src.core.security import get_current_user
from src.modules.social.schemas import FeedPost, FeedPostCreate, SupportResponse
from src.modules.social.service import (
    add_support,
    create_post,
    list_feed,
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
