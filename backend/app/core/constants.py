from enum import Enum


class TeachingStyle(str, Enum):
    BEGINNER = "beginner"
    STEP_BY_STEP = "step_by_step"
    ACADEMIC = "academic"
    FAST_SUMMARY = "fast_summary"
    VISUAL = "visual"
    REAL_LIFE_EXAMPLES = "real_life_examples"
    QUIZ = "quiz"


class LearningMode(str, Enum):
    TEXT = "text"
    IMAGES = "images"
    INTERACTIVE = "interactive"
    VIDEO = "video"


class SubscriptionStatus(str, Enum):
    FREE = "free"
    TRIAL = "trial"
    PREMIUM = "premium"
    EXPIRED = "expired"


class PreferredLanguage(str, Enum):
    ARABIC = "ar"
    ENGLISH = "en"


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class SourceType(str, Enum): 
    TEXTBOOK = "textbook" 
    TEACHER_GUIDE = "teacher_guide" 
    EXAMS = "exams" 
    

class AnswerScope(str, Enum): 
    BOOK_ONLY = "book_only" 
    GENERAL = "general" 
    HYBRID = "hybrid"

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

LESSONS = {
    "المحاليل المائية": (1, 8),
    "المحاليل الحمضية": (9, 16),
    "المحاليل الأساسية": (17, 24),
    "أنواع التفاعلات الكيميائية": (25, 38),
    "الأملاح": (39, 49),
    "مدخل إلى الكيمياء العضوية": (55, 63),
    "المركبات الهدروكربونية": (64, 64),
    "الألكانات (البارافينات)": (65, 70),
    "المركبات الهدروكربونية غير المشبعة": (71, 77),
    "النشاط الإشعاعي": (85, 92),
}

QUESTION_TYPES = {
    "MCQ": "Multiple choice, 4 options, exactly one correct answer",
    "True/False": "True or false question",
    "Fill": "Fill in the blank",
    "Calculation": "Calculation problem with steps",
    "Explanation": "Explanation / reasoning question",
}