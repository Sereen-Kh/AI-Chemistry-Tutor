"""Model registry.

Import every SQLAlchemy model here so Alembic autogeneration and schema
verification can see the complete ORM metadata.
"""

from app.models.enums import LearningMode, TeachingStyle  # noqa: F401
from app.models.achievement import Achievement  # noqa: F401
from app.models.assessment import Question, QuestionAttempt, QuizAttempt  # noqa: F401
from app.models.billing import Subscription  # noqa: F401
from app.models.chat import ChatMessage, ChatSession  # noqa: F401
from app.models.chemistry import Chapter, Element, Lesson, LessonProgress, Unit  # noqa: F401
from app.models.device import DeviceToken  # noqa: F401
from app.models.flashcard import Flashcard, FlashcardProgress  # noqa: F401
from app.models.homework import Homework  # noqa: F401
from app.models.interest import InterestCategory, UserInterest  # noqa: F401
from app.models.ingestion import IngestionJob, IngestionPage  # noqa: F401
from app.models.interactive_solver import (  # noqa: F401
    InteractiveSession,
    InteractiveStep,
    MisconceptionEvent,
    SkillMastery,
    StudentStepAnswer,
)
from app.models.reel import Reel  # noqa: F401
from app.models.rag_logging import RagQueryLog, RetrievedChunkLog  # noqa: F401
from app.models.student_profile import StudentProfile  # noqa: F401
from app.models.study_plan import StudyPlan  # noqa: F401
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk, TextbookChunk  # noqa: F401
from app.models.topic import Topic  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_progress import UserProgress  # noqa: F401
from app.models.notification import Notification, NotificationPreference, ReminderEvent  # noqa: F401
