from sqlalchemy.orm import Session
import uuid
from app.repositories.question_repository import QuestionRepository
from app.services.question_generator import QuestionGenerator
from app.models.generated_question import GeneratedQuestion


class QuestionService:
    MIN_BANK_SIZE = 15

    @staticmethod
    def get_questions(
        db: Session,
        lesson: str,
        question_type: str,
        difficulty: str,
        count: int,
        exclude_ids: list[str] | None = None,
    ):
    
        print("1. Fetch from question bank")
    
    
        available = QuestionRepository.count(
            db,
            lesson,
            question_type,
            difficulty,
        )
    
    
        print(f"Available questions: {available}")
    
    
        if available < QuestionService.MIN_BANK_SIZE:
    
            needed = (
                QuestionService.MIN_BANK_SIZE
                -
                available
            )
    
    
            print(
                f"Generating {needed} questions"
            )
    
    
            generated_questions = (
                QuestionGenerator.generate_and_review(
                    lesson=lesson,
                    count=needed,
                    difficulty=difficulty,
                    question_type=question_type,
                )
            )
    
    
            db_objects = []
    
    
            for q in generated_questions:
    
                db_objects.append(
                    GeneratedQuestion(
                        id=uuid.UUID(q["id"]),
                        lesson=q["lesson"],
                        question_type=q["question_type"],
                        difficulty=q["difficulty"],
                        question=q["question"],
                        options=q.get("options", []),
                        answer=q["answer"],
                        explanation=q["explanation"],
                    )
                )
    
    
            if db_objects:
                QuestionRepository.create_many(
                    db,
                    db_objects,
                )
    
    
        print("2. Return requested questions")
    
    
        return QuestionRepository.fetch(
            db=db,
            lesson=lesson,
            question_type=question_type,
            difficulty=difficulty,
            exclude_ids=exclude_ids,
            limit=count,
        )