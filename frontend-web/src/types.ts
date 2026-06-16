export type TeachingLevel = 'simple' | 'standard' | 'academic';
export type ExplanationMethod = 'direct' | 'step_by_step' | 'hints_first' | 'exam_mode' | 'real_life_example';
export type LearningMode = 'text' | 'image' | 'audio' | 'video' | 'reel' | 'interactive' | 'quiz' | 'flashcards';
export type StudentInterest = 'football' | 'cars' | 'cooking' | 'gaming' | 'daily_life' | 'laboratory' | 'nature' | 'none';
export type TeachingStyle = 'simple' | 'real_life' | 'visual' | 'exam';
export type AnswerFormat = Extract<LearningMode, 'text' | 'audio' | 'image' | 'video'>;
export type LessonStatus = 'completed' | 'current' | 'locked' | 'weak';
export type CurriculumEntityId = string | number;

export interface TopicCatalogItem {
  id: number;
  title_ar: string;
  title_en?: string | null;
  description_ar?: string | null;
  category?: string | null;
  difficulty: number;
  icon?: string | null;
  order: number;
}

export interface LessonCatalogItem {
  id: number;
  chapter_id: number;
  title_ar: string;
  title_en?: string | null;
  content_ar: string;
  order: number;
  difficulty: number;
  duration_min: number;
  page_start?: number | null;
  page_end?: number | null;
  topics: TopicCatalogItem[];
  created_at?: string;
  updated_at?: string;
}

export interface ChapterCatalogItem {
  id: number;
  unit_id?: number | null;
  title_ar: string;
  title_en?: string | null;
  description_ar?: string | null;
  order: number;
  difficulty: number;
  icon?: string | null;
  lessons: LessonCatalogItem[];
  created_at?: string;
  updated_at?: string;
}

export interface UnitCatalogItem {
  id: number;
  unit_number: number;
  semester: number;
  title_ar: string;
  title_en?: string | null;
  description_ar?: string | null;
  order: number;
  icon?: string | null;
  chapters: ChapterCatalogItem[];
  created_at?: string;
  updated_at?: string;
}

export interface UserPreferences {
  interests: string[];
  teachingStyle?: TeachingStyle;
  answerFormat?: AnswerFormat;
  teachingLevel: TeachingLevel;
  explanationMethod: ExplanationMethod;
  learningModes: LearningMode[];
  studentInterests: StudentInterest[];
  language: 'ar' | 'en';
  grade: string;
  subject: string;
}

export interface UserProfile {
  id: number;
  name: string;
  first_name?: string;
  last_name?: string;
  email: string;
  grade: string;
  subject: string;
  teaching_style: string;
  answer_format: string;
  teaching_level?: TeachingLevel;
  explanation_method?: ExplanationMethod;
  learning_modes?: LearningMode[];
  student_interests?: StudentInterest[];
  language: string;
  xp: number;
  level: number;
  streak_days: number;
}

export interface InterestCategory {
  id: number;
  key: string;
  name_ar: string;
  name_en?: string | null;
  icon?: string | null;
}

export interface SourceCitation {
  title: string;
  page: number | null;
  chunk_id: string | number;
  quote?: string;
  score?: number;
}

export interface AiAskRequest {
  conversation_id?: string;
  parent_message_id?: string;
  question: string;
  subject: string;
  grade: string;
  answer_format: AnswerFormat;
  teaching_style?: TeachingStyle;
  teaching_level?: TeachingLevel;
  explanation_method?: ExplanationMethod;
  learning_modes?: LearningMode[];
  student_interests?: StudentInterest[];
  interests?: string[];
  language: 'ar' | 'en';
  answer_scope?: 'auto' | 'book_only' | 'tutor_general';
  source_types?: string[];
  action?: 'rephrase_previous' | 'try_differently' | 'simplify_previous';
  previous_question?: string;
  previous_answer?: string;
  previous_sources?: SourceCitation[];
  previous_selected_chunks?: Record<string, unknown>[];
}

export interface AiAskResponse {
  answer: string;
  answer_text?: string;
  sources: SourceCitation[];
  citations?: SourceCitation[];
  confidence: number;
  format: AnswerFormat;
  teaching_level?: TeachingLevel;
  explanation_method?: ExplanationMethod;
  learning_modes?: LearningMode[];
  student_interests?: StudentInterest[];
  media_blocks?: Array<Record<string, unknown>>;
  answer_type?: string;
  route?: string;
  diagnostics?: Record<string, unknown>;
  audio_url?: string;
  image_url?: string;
  source_page_image_url?: string;
  video_url?: string;
  video_title?: string;
  video_source?: 'internal' | 'youtube' | 'instagram';
}

export interface ChatMessageResponse {
  id: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  answer_text?: string | null;
  format: AnswerFormat | string;
  feedback?: string | null;
  media_url?: string | null;
  latency_ms?: number | null;
  confidence?: number | null;
  answer_type?: string | null;
  route?: string | null;
  grounding?: string | null;
  sources?: Array<Record<string, unknown>>;
  citations?: Array<Record<string, unknown>>;
  blocks?: Array<Record<string, unknown>>;
  media_blocks?: Array<Record<string, unknown>>;
  source_blocks?: Array<Record<string, unknown>>;
  page_numbers?: number[];
  diagnostics?: Record<string, unknown>;
  suggested_next_action?: string | null;
  created_at: string;
}

export interface ChatSessionResponse {
  id: number;
  user_id: number;
  lesson_id?: number | null;
  title?: string | null;
  style?: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessageResponse[];
}

export interface ChatSessionCreateRequest {
  title?: string | null;
  lesson_id?: number | null;
  style?: string | null;
}

export interface SendSessionMessageRequest {
  content: string;
  format?: AnswerFormat;
  answer_scope?: AiAskRequest['answer_scope'];
  source_types?: string[];
  teaching_style?: TeachingStyle;
  teaching_level?: TeachingLevel;
  explanation_method?: ExplanationMethod;
  learning_modes?: LearningMode[];
  student_interests?: StudentInterest[];
  action?: AiAskRequest['action'];
}

export interface LessonItem {
  id: number;
  title: string;
  duration: number;
  status: LessonStatus;
}

export interface ChapterPlan {
  id: number;
  title: string;
  subtitle: string;
  progress: number;
  color: 'blue' | 'teal' | 'gold' | 'coral' | 'purple';
  lessons: LessonItem[];
}

export interface StudyPlan {
  id?: string;
  chapters: ChapterPlan[];
  weakTopics: string[];
  currentLesson: LessonItem;
  config?: {
    title?: string;
    examDate?: string;
    startDate?: string;
    endDate?: string;
    lessonIds?: Array<string | number>;
    [key: string]: unknown;
  };
}

export interface FlashcardDeck {
  id: number;
  title: string;
  topic: string;
  count: number;
  mastered: number;
  cards: FlashcardItem[];
}

export interface FlashcardItem {
  id: number;
  front: string;
  back: string;
  hint?: string;
}

export interface BalanceResult {
  input: string;
  balanced: string;
  explanation: string[];
}

export type LessonQualityReport = {
  lessonId: string;
  status: 'ready' | 'needs_review' | 'blocked';
  score: number;
  checks: {
    hasTitle: boolean;
    hasSourcePages: boolean;
    hasEnoughText: boolean;
    hasObjectives: boolean;
    hasKeyTerms: boolean;
    hasDefinitions: boolean;
    hasEquations: boolean;
    hasExamples: boolean;
    hasExercises: boolean;
    hasValidRagChunks: boolean;
    hasNoOcrGaps: boolean;
  };
  issues: string[];
};

export type LessonKnowledgeUnit = {
  lessonId: string;
  chapterId: string;
  titleAr: string;
  pageStart: number;
  pageEnd: number;
  objectives: string[];
  keyTerms: {
    term: string;
    definition: string;
    sourcePage: number;
  }[];
  definitions: {
    concept: string;
    explanation: string;
    sourcePage: number;
  }[];
  equations: {
    latex: string;
    explanation: string;
    variables: string[];
    sourcePage: number;
  }[];
  examples: {
    question: string;
    solution: string;
    sourcePage: number;
  }[];
  experiments: {
    title: string;
    materials: string[];
    steps: string[];
    conclusion: string;
    sourcePage: number;
  }[];
  exercises: {
    question: string;
    answer?: string;
    sourcePage: number;
  }[];
  ragChunkIds: string[];
  qualityScore: number;
};

export type QuizGenerationConfig = {
  mode:
    | 'single_lesson'
    | 'selected_lessons'
    | 'chapter'
    | 'weak_lessons'
    | 'study_plan'
    | 'exam_review';
  lessonIds: CurriculumEntityId[];
  chapterIds?: string[];
  questionsPerLesson: number;
  totalQuestions?: number;
  difficulty: 'easy' | 'medium' | 'hard' | 'mixed';
  questionTypes: Array<
    | 'mcq'
    | 'true_false'
    | 'fill_blank'
    | 'short_answer'
    | 'calculation'
    | 'equation_balancing'
  >;
  includeSourcePage: boolean;
  requireExplanation: boolean;
  avoidDuplicateQuestions: boolean;
};

export type GeneratedQuizQuestion = {
  id: string;
  lessonId: string;
  chapterId: string;
  questionType:
    | 'mcq'
    | 'true_false'
    | 'fill_blank'
    | 'short_answer'
    | 'calculation'
    | 'equation_balancing';
  question: string;
  options?: string[];
  correctAnswer: string;
  correctOptionIndex?: number;
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
  sourcePage: number;
  sourceChunkId?: string;
};

export type FlashcardGenerationConfig = {
  mode:
    | 'single_lesson'
    | 'selected_lessons'
    | 'chapter'
    | 'weak_lessons'
    | 'study_plan';
  lessonIds: CurriculumEntityId[];
  cardsPerLesson: number;
  cardTypes: Array<
    | 'definition'
    | 'formula'
    | 'term'
    | 'reaction'
    | 'comparison'
    | 'experiment'
    | 'common_mistake'
  >;
  difficulty: 'easy' | 'medium' | 'hard' | 'mixed';
  includeSourcePage: boolean;
  spacedRepetitionEnabled: boolean;
};

export type GeneratedFlashcard = {
  id: string;
  lessonId: string;
  chapterId: string;
  front: string;
  back: string;
  cardType:
    | 'definition'
    | 'formula'
    | 'term'
    | 'reaction'
    | 'comparison'
    | 'experiment'
    | 'common_mistake';
  difficulty: 'easy' | 'medium' | 'hard';
  sourcePage: number;
  sourceChunkId?: string;
  reviewState: 'new' | 'learning' | 'known' | 'review';
  nextReviewAt?: string;
};

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: 'exam' | 'lesson' | 'quiz' | 'system';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'read' | 'unread';
  scheduled_at: string;
  related_entity_type?: 'lesson' | 'quiz' | 'flashcard' | 'plan';
  related_entity_id?: string;
  action_label?: string;
  action_url?: string;
}

export interface SemesterPlanConfig {
  startDate: string;
  endDate: string;
  studyDays: string[];
  lessonDuration: string;
  weeklyRest: string;
  lessonIds: CurriculumEntityId[];
}

export interface ExamPlanConfig {
  title: string;
  examDate: string;
  dailyStudyHours: string;
  priority: string;
  lessonIds: CurriculumEntityId[];
}
