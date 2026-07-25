import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import (
    ChatResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
)
from app.services.chat_service import ChatService


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# =====================================
# Conversations
# =====================================

@router.post(
    "/conversations",
    response_model=
    ConversationResponse,

    status_code=
    status
    .HTTP_201_CREATED
)
def create_conversation(
    data:
    CreateConversationRequest,

    db: Session = Depends(
        get_db
    ),

    current_user:
    User = Depends(
        get_current_user
    )
):

    return (
        ChatService
        .create_conversation(
            db,
            current_user,
            data
        )
    )


@router.get(
    "/conversations",
    response_model=
    ConversationListResponse
)
def get_conversations(
    db: Session = Depends(
        get_db
    ),

    current_user:
    User = Depends(
        get_current_user
    )
):

    conversations = (
        ChatService
        .get_conversations(
            db,
            current_user
        )
    )

    return {
        "conversations":
        conversations
    }


@router.get(
    "/conversations/{conversation_id}",
    response_model=
    list[MessageResponse]
)
def get_conversation_messages(
    conversation_id:
    uuid.UUID,

    db: Session = Depends(
        get_db
    ),

    current_user:
    User = Depends(
        get_current_user
    )
):

    conversation = (
        ChatService
        .get_conversation(
            db,
            current_user,
            conversation_id
        )
    )

    return (
        MessageRepository
        .get_conversation_messages(
            db,
            conversation.id
        )
    )


# =====================================
# Messaging
# =====================================

@router.post(
    "/send",
    response_model=ChatResponse
)
async def send_message(
    data:
    SendMessageRequest,

    db: Session = Depends(
        get_db
    ),

    current_user:
    User = Depends(
        get_current_user
    )
):

    return await (
        ChatService
        .send_message(
            db=db,
            user=current_user,

            conversation_id= data.conversation_id,

            question= data.message
        )
    )


# =====================================
# Delete
# =====================================

@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK
)
def delete_conversation(
    conversation_id:
    uuid.UUID,

    db: Session = Depends(
        get_db
    ),

    current_user:
    User = Depends(
        get_current_user
    )
):

    ChatService.delete_conversation(
        db,
        current_user,
        conversation_id
    )
    return {"message": "Conversation deleted successfully"}
