from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AppRole(StrEnum):
    PATIENT = "patient"
    EXPERT_PATIENT = "expert_patient"


class PostType(StrEnum):
    POST = "post"
    ACHIEVEMENT = "achievement"


class SessionKind(StrEnum):
    GROUP = "group"
    INDIVIDUAL = "individual"


class PatientProfile(BaseModel):
    id: int
    full_name: str
    role: AppRole
    privacy_level: str
    main_goal: str
    weekly_activity_minutes: int = Field(ge=0)
    challenge_completion_rate: int = Field(ge=0, le=100)


class FeedPostCreate(BaseModel):
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


class Challenge(BaseModel):
    id: int
    title: str
    description: str
    category: str
    progress: int = Field(ge=0, le=100)
    due_on: date


class Progression(BaseModel):
    weekly_activity_minutes: int = Field(ge=0)
    challenge_completion_rate: int = Field(ge=0, le=100)
    current_streak_days: int = Field(ge=0)
    active_challenges: list[Challenge]


class RestaurantRecommendation(BaseModel):
    id: int
    name: str
    area: str
    diabetes_friendly_score: int = Field(ge=0, le=100)
    best_for: str
    notes: str


class Conversation(BaseModel):
    id: int
    contact_name: str
    contact_role: AppRole
    last_message: str
    unread_count: int = Field(ge=0)
    updated_at: datetime


class PrivacySettingsUpdate(BaseModel):
    privacy_level: str


class PatientSettings(BaseModel):
    profile: PatientProfile
    share_activity: bool
    share_challenges: bool
    share_restaurants: bool


class SupportSessionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    kind: SessionKind
    scheduled_for: datetime
    capacity: int = Field(ge=1, le=30)
    notes: str = Field(default="", max_length=300)


class SupportSession(BaseModel):
    id: int
    expert_patient_id: int
    title: str
    kind: SessionKind
    scheduled_for: datetime
    capacity: int
    enrolled_count: int = Field(ge=0)
    notes: str
