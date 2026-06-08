from enum import Enum


class TeachingStyle(str, Enum):
    BEGINNER = "beginner"
    STEP_BY_STEP = "step_by_step"
    ACADEMIC = "academic"
    FAST_SUMMARY = "fast_summary"
    VISUAL = "visual"
    REAL_LIFE_EXAMPLES = "real_life_examples"


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