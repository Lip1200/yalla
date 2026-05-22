from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ChallengeCategory(StrEnum):
    ACTIVITY = "activity"
    NUTRITION = "nutrition"
    COMMUNITY = "community"
    MINDFULNESS = "mindfulness"


class ChallengeDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ChallengeUnit(StrEnum):
    MINUTES = "minutes"
    STEPS = "steps"
    DAYS = "days"
    MEALS = "meals"
    SESSIONS = "sessions"


class ChallengeStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ChallengeBase(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    category: ChallengeCategory = ChallengeCategory.ACTIVITY
    target_value: int = Field(gt=0)
    target_unit: ChallengeUnit = ChallengeUnit.MINUTES
    duration_days: int = Field(default=7, ge=1, le=90)
    difficulty: ChallengeDifficulty = ChallengeDifficulty.MEDIUM
    is_template: bool = True


class ChallengeCreate(ChallengeBase):
    pass


class ChallengeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category: ChallengeCategory | None = None
    target_value: int | None = Field(default=None, gt=0)
    target_unit: ChallengeUnit | None = None
    duration_days: int | None = Field(default=None, ge=1, le=90)
    difficulty: ChallengeDifficulty | None = None
    is_template: bool | None = None


class Challenge(ChallengeBase):
    id: int
    created_at: datetime


class PatientChallengeAssign(BaseModel):
    patient_id: int
    challenge_id: int
    due_on: date | None = None  # Defaults to started_at + challenge.duration_days


class PatientChallengeProgressUpdate(BaseModel):
    current_value: int | None = Field(default=None, ge=0)
    progress: int | None = Field(default=None, ge=0, le=100)
    status: ChallengeStatus | None = None


class PatientChallenge(BaseModel):
    id: int
    patient_id: int
    challenge_id: int
    challenge: Challenge
    progress: int = Field(ge=0, le=100)
    current_value: int = Field(ge=0)
    started_at: datetime
    due_on: date
    completed_at: datetime | None = None
    status: ChallengeStatus
