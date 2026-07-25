import time
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.core.constants import AnswerScope, MessageRole, SourceType, TeachingStyle
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatResponse, CreateConversationRequest
from app.services.llm_gateway import LLMGateway


class ChatService:

    @staticmethod
    def create_conversation(
        db: Session,
        user: User,
        data:
        CreateConversationRequest
        ) -> Conversation:

        conversation = (
            Conversation(
                user_id=user.id,
                title=data.title
            )
        )

        return (
            ConversationRepository.create(
                db,
                conversation
            )
        )

    @staticmethod
    def get_conversations(
        db: Session,
        user: User
        ) -> list[Conversation]:

        return (
            ConversationRepository.get_user_conversations(
                db,
                user.id
            )
        )

    @staticmethod
    def get_conversation(
        db: Session,
        user: User,
        conversation_id:
        uuid.UUID
        ) -> Conversation:

        conversation = (
            ConversationRepository.get_by_id(
                db,
                conversation_id
            )
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail= "Conversation not found"
            )

        if (conversation.user_id!= user.id):
            raise HTTPException(
                status_code= status.HTTP_403_FORBIDDEN,
                detail= ("Not authorized")
            )

        return conversation

    @staticmethod
    async def send_message(
        db: Session,
        user: User,
        conversation_id:
        uuid.UUID,
        question: str
        ) -> ChatResponse:

        conversation = (
            ChatService.get_conversation(
                db,
                user,
                conversation_id
            )
        )
        if conversation.is_processing:
            raise HTTPException(
                409,
                detail="Conversation is already processing a message"
            )

        # Save user message
        user_message = (
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER.value,
                content=question
            )
        )

        user_message = (
            MessageRepository.create(
                db,
                user_message
            )
        )

        # Get recent history
        recent_messages = (
            MessageRepository.get_recent_messages(
                db,
                conversation.id,
                limit=5
            )
        )

        history = []

        for msg in recent_messages:
            history.append({
                "role":msg.role,
                "content":msg.content
            })

        # Model Call
        start_time = (time.perf_counter())
        conversation.is_processing = True
        ConversationRepository.update(db,conversation)

        try:
            
            ai_response = (
                await LLMGateway.ask(
                            question=question,
                            teaching_style=TeachingStyle(user.preference.preferred_teaching_style),
                            history=history
                            )
                        )
        finally: 
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            assistant_message = (Message(
                                    conversation_id=conversation.id,
                                    role=MessageRole.ASSISTANT.value,
                                    content=ai_response["answer"],
                                    sources=ai_response["sources"],
                                    latency_ms=latency_ms
                                )
                            )

            assistant_message = (MessageRepository.create(db,assistant_message))

            conversation.updated_at = (assistant_message.created_at)

            conversation.is_processing = False
            ConversationRepository.update(db,conversation)

            return ChatResponse(
                conversation_id=conversation.id,
                user_message=user_message,
                assistant_message=assistant_message
            )

    @staticmethod
    def delete_conversation(
        db: Session,
        user: User,
        conversation_id:
        uuid.UUID
    ) -> None:

        conversation = (
            ChatService
            .get_conversation(
                db,
                user,
                conversation_id
            )
        )

        ConversationRepository.delete(db,conversation)
