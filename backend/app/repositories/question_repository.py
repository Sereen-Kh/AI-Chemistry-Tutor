import uuid
import random

from sqlalchemy.orm import Session

from app.models.generated_question import GeneratedQuestion


class QuestionRepository:


    @staticmethod
    def create_many(
        db: Session,
        questions: list[GeneratedQuestion],
    ) -> list[GeneratedQuestion]:

        db.add_all(questions)
        db.commit()

        for question in questions:
            db.refresh(question)

        return questions


    @staticmethod
    def count(
        db: Session,
        lesson: str,
        question_type: str,
        difficulty: str,
    ) -> int:

        return (
            db.query(GeneratedQuestion)
            .filter(
                GeneratedQuestion.lesson == lesson,
                GeneratedQuestion.question_type == question_type,
                GeneratedQuestion.difficulty == difficulty,
            )
            .count()
        )

    @staticmethod
    def fetch(
        db: Session,
        lesson: str,
        question_type: str,
        difficulty: str,
        exclude_ids: list[str] | None = None,
        limit: int = 5,
    ) -> list[GeneratedQuestion]:
    
        query = (
            db.query(GeneratedQuestion)
            .filter(
                GeneratedQuestion.lesson == lesson,
                GeneratedQuestion.question_type == question_type,
                GeneratedQuestion.difficulty == difficulty,
            )
        )
    
    
        if exclude_ids:
            exclude_ids = [uuid.UUID(x) for x in exclude_ids]
            query = query.filter(~GeneratedQuestion.id.in_(exclude_ids))
        questions = query.all()
        random.shuffle(questions)
        return questions[:limit]

    @staticmethod
    def get_by_id(
        db: Session,
        question_id: uuid.UUID,
    ) -> GeneratedQuestion | None:

        return (
            db.query(GeneratedQuestion)
            .filter(
                GeneratedQuestion.id == question_id
            )
            .first()
        )


    @staticmethod
    def delete(
        db: Session,
        question: GeneratedQuestion,
    ) -> None:

        db.delete(question)
        db.commit()