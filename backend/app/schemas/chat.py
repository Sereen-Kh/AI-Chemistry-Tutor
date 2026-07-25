from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# Conversation
# -------------------------

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="New Chat", max_length=200)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = (
        ConfigDict(
            from_attributes=True
        )
    )


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


# Message
# -------------------------

class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[list[dict]] = None

    latency_ms: Optional[int] = None

    created_at: datetime

    model_config = (
        ConfigDict(
            from_attributes=True
        )
    )


# -------------------------
# Chat
# -------------------------

class SendMessageRequest(BaseModel):
    conversation_id: uuid.UUID
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message: MessageResponse
    assistant_message:MessageResponse