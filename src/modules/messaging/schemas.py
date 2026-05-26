from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ConversationKind(StrEnum):
    DIRECT = "direct"
    GROUP = "group"


class ConversationParticipantSummary(BaseModel):
    user_id: int
    full_name: str
    role: str


class Conversation(BaseModel):
    id: int
    kind: ConversationKind
    title: str | None = None
    participants: list[ConversationParticipantSummary]
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = Field(ge=0)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class Message(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_name: str
    content: str
    sent_at: datetime
    is_mine: bool = False


class DirectConversationCreate(BaseModel):
    """Open or retrieve the 1-on-1 conversation between the caller and
    `other_user_id`. Idempotent — calling twice returns the same row."""

    other_user_id: int = Field(gt=0)


class MarkReadResponse(BaseModel):
    conversation_id: int
    last_read_at: datetime
