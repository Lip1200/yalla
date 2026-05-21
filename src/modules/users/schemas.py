from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    PATIENT = "patient"
    EXPERT_PATIENT = "expert_patient"
    DOCTOR = "doctor"


class PrivacyLevel(StrEnum):
    SHARED = "Données partagées"
    LIMITED = "Données limitées"
    PRIVATE = "Données privées"


class ProfileBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    role: UserRole = UserRole.PATIENT
    privacy_level: str = Field(default=PrivacyLevel.LIMITED.value, max_length=80)
    primary_goal: str = Field(default="", max_length=200)
    age: int | None = Field(default=None, ge=0, le=150)
    weekly_activity_minutes: int = Field(default=0, ge=0)
    challenge_completion_rate: int = Field(default=0, ge=0, le=100)
    activity_completion_rate: int = Field(default=0, ge=0, le=100)
    has_app_access: bool = True
    last_check_in: date | None = None
    status: str | None = Field(default=None, max_length=80)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    privacy_level: str | None = Field(default=None, max_length=80)
    primary_goal: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=0, le=150)
    weekly_activity_minutes: int | None = Field(default=None, ge=0)
    challenge_completion_rate: int | None = Field(default=None, ge=0, le=100)
    activity_completion_rate: int | None = Field(default=None, ge=0, le=100)
    has_app_access: bool | None = None
    last_check_in: date | None = None
    status: str | None = Field(default=None, max_length=80)


class ProfileReplace(ProfileBase):
    pass


class Profile(ProfileBase):
    id: int
