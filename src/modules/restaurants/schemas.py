from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PoolStatus(StrEnum):
    OPEN = "open"
    FULL = "full"
    BOOKED = "booked"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# --- Curated Restaurant ---

class CuratedRestaurant(BaseModel):
    id: int
    thefork_restaurant_id: str
    name: str
    area: str
    cuisine_type: str = ""
    diabetes_friendly_score: int = Field(ge=0, le=100)
    best_for: str = ""
    notes: str = ""
    image_url: str = ""


# --- Pool ---

class PoolCreate(BaseModel):
    restaurant_id: int
    scheduled_for: datetime
    capacity: int = Field(ge=2, le=20)
    customer_note: str = Field(default="", max_length=300)


class PoolParticipant(BaseModel):
    user_id: int
    full_name: str
    joined_at: datetime


class PoolResponse(BaseModel):
    id: int
    creator_id: int
    creator_name: str
    restaurant: CuratedRestaurant
    scheduled_for: datetime
    capacity: int
    enrolled_count: int = Field(ge=0)
    status: PoolStatus
    customer_note: str = ""
    thefork_reservation_id: str | None = None
    participants: list[PoolParticipant] = []
    created_at: datetime


class PoolJoinResult(BaseModel):
    pool: PoolResponse
    auto_booked: bool
