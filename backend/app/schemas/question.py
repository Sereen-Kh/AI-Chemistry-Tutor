from pydantic import BaseModel, Field


class GenerateQuestionsRequest(BaseModel):
    lesson: str
    question_type: str
    difficulty: str = "medium"
    count: int = Field(default=5, ge=1, le=20)
    exclude_ids: list[str] | None = None


class QuestionItemResponse(BaseModel):
    id: str
    question: str
    options: list[str] = Field(default_factory=list)
    answer: str
    explanation: str


class GenerateQuestionsResponse(BaseModel):
    lesson: str
    question_type: str
    difficulty: str
    questions: list[QuestionItemResponse]


class LessonItem(BaseModel):
    name: str
    start_page: int
    end_page: int


class LessonsResponse(BaseModel):
    lessons: list[LessonItem]


from pydantic import BaseModel


class QuestionTypeItem(BaseModel):
    name: str
    description: str


class QuestionTypesResponse(BaseModel):
    question_types: list[QuestionTypeItem]