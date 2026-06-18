export type LearningPage =
  | 'home'
  | 'lessons'
  | 'lesson_detail'
  | 'study_plan'
  | 'book_search'
  | 'quiz'
  | 'flashcards'
  | 'ask_ai'
  | 'lab'
  | 'homework'
  | 'notifications'
  | 'profile'
  | 'admin'
  | 'unknown';

export type LearningContext = {
  userId?: string;
  currentPage: LearningPage;
  currentRoute: string;
  activeSemester?: 1 | 2;
  activeUnitId?: number;
  activeChapterId?: number;
  activeLessonId?: number;
  activeTopicId?: number;
  activeUnitTitleAr?: string;
  activeChapterTitleAr?: string;
  activeLessonTitleAr?: string;
  activeTopicTitleAr?: string;
  progressPercent?: number;
  dailyMission?: {
    titleAr: string;
    lessonId?: number;
    topicId?: number;
    estimatedMinutes?: number;
  };
  weakTopics?: Array<{
    topicId: number;
    titleAr: string;
    scorePercent: number;
  }>;
  nextExamDate?: string;
  scrollSection?: string;
};

export type CompanionActionKind =
  | 'explain_lesson'
  | 'book_order'
  | 'show_topics'
  | 'quiz'
  | 'plan_today'
  | 'weak_topics'
  | 'exam_review'
  | 'flashcards'
  | 'ask_ai'
  | 'homework_to_solver';

export type CompanionAction = {
  id: string;
  label: string;
  description?: string;
  kind: CompanionActionKind;
  targetRoute?: string;
};

export type CompanionSuggestionResponse = {
  message: string;
  suggestedActions: CompanionAction[];
  targetRoute?: string;
};

export type CompanionMessageResponse = CompanionSuggestionResponse & {
  responseMode?: 'text' | 'action';
};

export type CompanionChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: number;
};
