from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.question import (
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    LessonItem,
    LessonsResponse,
    QuestionTypesResponse,
)

from app.services.question_service import QuestionService
from app.core.constants import LESSONS, QUESTION_TYPES

router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)

@router.post("/generate",response_model=GenerateQuestionsResponse,)
def generate_questions(
    data: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    current_user:User = Depends(get_current_user),
    
    ):
    print("GENERATE STARTED")

    questions = QuestionService.get_questions(
        db=db,
        lesson=data.lesson,
        question_type=data.question_type,
        difficulty=data.difficulty,
        count=data.count,
        exclude_ids=data.exclude_ids,
    )
    print(type(questions))
    print(questions)



    response =  {
        "lesson": data.lesson,
        "question_type": data.question_type,
        "difficulty": data.difficulty,
        "questions": [
            {
                "id": str(q.id),
                "question": q.question,
                "options": q.options or [],
                "answer": q.answer,
                "explanation": q.explanation,
            }
            for q in questions
        ],
    }
    print(response)
    return response

@router.get("/lessons", response_model=LessonsResponse)
def get_lessons():

    lessons = [
        LessonItem(
            name=name,
            start_page=pages[0],
            end_page=pages[1]
        )
        for name, pages in LESSONS.items()
    ]

    return {
        "lessons": lessons
    }

@router.get("/question-types", response_model=QuestionTypesResponse)
def get_question_types(
    current_user: User = Depends(get_current_user),
):
    return {
        "question_types": [
            {
                "name": name,
                "description": description
            }
            for name, description in QUESTION_TYPES.items()
        ]
    }