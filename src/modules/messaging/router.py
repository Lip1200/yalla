from fastapi import APIRouter, Depends, Query, status

from src.core.security import AuthIdentity, get_current_user
from src.modules.messaging.schemas import (
    Conversation,
    DirectConversationCreate,
    MarkReadResponse,
    Message,
    MessageCreate,
)
from src.modules.messaging.service import (
    get_thread,
    list_my_conversations,
    mark_read,
    open_direct_conversation,
    send_message,
)

router = APIRouter()


@router.get("/conversations", response_model=list[Conversation])
def read_conversations(
    user_id: int | None = Query(default=None, description="Required for service token; ignored for real users."),
    identity: AuthIdentity = Depends(get_current_user),
):
    return list_my_conversations(identity, user_id_override=user_id)


@router.post(
    "/conversations/direct",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
)
def post_direct_conversation(
    payload: DirectConversationCreate,
    user_id: int | None = Query(default=None),
    identity: AuthIdentity = Depends(get_current_user),
):
    return open_direct_conversation(identity, payload, user_id_override=user_id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[Message],
)
def read_messages(
    conversation_id: int,
    limit: int = 50,
    user_id: int | None = Query(default=None),
    identity: AuthIdentity = Depends(get_current_user),
):
    return get_thread(identity, conversation_id, limit=limit, user_id_override=user_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    conversation_id: int,
    payload: MessageCreate,
    user_id: int | None = Query(default=None),
    identity: AuthIdentity = Depends(get_current_user),
):
    return send_message(identity, conversation_id, payload, user_id_override=user_id)


@router.patch(
    "/conversations/{conversation_id}/read",
    response_model=MarkReadResponse,
)
def patch_mark_read(
    conversation_id: int,
    user_id: int | None = Query(default=None),
    identity: AuthIdentity = Depends(get_current_user),
):
    return mark_read(identity, conversation_id, user_id_override=user_id)
