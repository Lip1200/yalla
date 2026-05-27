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


class GroupCategory(StrEnum):
    WALKING = "walking"
    COOKING = "cooking"
    SUPPORT = "support"
    GENERAL = "general"


class GroupMemberRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    category: GroupCategory = GroupCategory.GENERAL
    creator_id: int


class Group(BaseModel):
    id: int
    name: str
    description: str
    category: GroupCategory
    creator_id: int
    creator_name: str
    member_count: int = Field(ge=0)
    created_at: datetime


class GroupMember(BaseModel):
    user_id: int
    full_name: str
    role: GroupMemberRole
    joined_at: datetime


class GroupDetail(Group):
    members: list[GroupMember]


class GroupJoinRequest(BaseModel):
    user_id: int


class FriendSuggestion(BaseModel):
    """Lightweight profile shown in the patient-app 'Ajouter des amis'
    carousel. Pulled from `profiles` (any role ∈ patient, expert_patient)
    minus the requester themself."""

    id: int
    name: str
    detail: str
    role: AppRole


class Friend(BaseModel):
    """A profile that the requester has explicitly added to their friends
    list. Returned by GET /api/social/friends/{patient_id}."""

    id: int
    name: str
    role: AppRole
    primary_goal: str = ""
    created_at: datetime


class FriendCreate(BaseModel):
    friend_id: int
