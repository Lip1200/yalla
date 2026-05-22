from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AppRole(StrEnum):
    PATIENT = "patient"
    EXPERT_PATIENT = "expert_patient"


class PostType(StrEnum):
    POST = "post"
    ACHIEVEMENT = "achievement"


class FeedPostCreate(BaseModel):
    author_id: int
    type: PostType = PostType.POST
    content: str = Field(min_length=2, max_length=500)
    achievement_label: str | None = Field(default=None, max_length=80)


class FeedPost(BaseModel):
    id: int
    author_id: int
    author_name: str
    author_role: AppRole
    type: PostType
    content: str
    achievement_label: str | None = None
    likes: int = Field(ge=0)
    comments_count: int = Field(ge=0)
    created_at: datetime


class SupportResponse(BaseModel):
    post_id: int
    likes: int = Field(ge=0)
