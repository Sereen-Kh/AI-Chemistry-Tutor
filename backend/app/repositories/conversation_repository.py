import uuid

from sqlalchemy.orm import Session
from app.models.conversation import Conversation


class ConversationRepository:

    @staticmethod
    def create(
        db: Session,
        conversation:
        Conversation
    ) -> Conversation:

        db.add(
            conversation
        )

        db.commit()

        db.refresh(
            conversation
        )

        return conversation

    @staticmethod
    def get_by_id(
        db: Session,
        conversation_id:
        uuid.UUID
    ) -> Conversation | None:

        return (
            db.query(
                Conversation
            )
            .filter(
                Conversation.id
                == conversation_id
            )
            .first()
        )

    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id:
        uuid.UUID
    ) -> list[Conversation]:

        return (
            db.query(
                Conversation
            )
            .filter(
                Conversation.user_id
                == user_id,

                Conversation
                .is_archived
                == False
            )
            .order_by(
                Conversation
                .updated_at
                .desc()
            )
            .all()
        )

    @staticmethod
    def update(
        db: Session,
        conversation:
        Conversation
    ) -> Conversation:

        db.commit()

        db.refresh(
            conversation
        )

        return conversation

    @staticmethod
    def delete(
        db: Session,
        conversation:
        Conversation
    ) -> None:

        db.delete(
            conversation
        )

        db.commit()