export type TeachingLevel = 'simple' | 'standard' | 'academic';
export type ExplanationMethod = 'direct' | 'step_by_step' | 'hints_first' | 'exam_mode' | 'real_life_example';
export type LearningMode = 'text' | 'image' | 'audio' | 'video' | 'reel' | 'interactive' | 'quiz' | 'flashcards';
export type PreferredResponseFormat = 'text' | 'audio' | 'image' | 'short_video' | 'interactive' | 'quiz' | 'flashcards';
export type StudentInterest = 'football' | 'cars' | 'cooking' | 'gaming' | 'daily_life' | 'laboratory' | 'nature' | 'none';
export type TeachingStyle =
  | 'simple' | 'real_life' | 'visual' | 'exam'
  | 'beginner' | 'step_by_step' | 'academic' | 'fast_summary' | 'real_life_examples';
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
  goals?: string;
  targetExamDate?: string;
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
  preferred_language?: string | null;
  goals?: string | null;
  target_exam_date?: string | null;
  onboarding_completed?: boolean;
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
  source_type?: string;
  unit_id?: string | number | null;
  lesson_id?: string | number | null;
  quality_status?: string | null;
  reviewed_metadata_version?: string | null;
  curriculum_metadata?: Record<string, unknown> | null;
}

export interface AiAskRequest {
  conversation_id?: string;
  parent_message_id?: string;
  question: string;
  subject: string;
  grade: string;
  lesson_id?: number | null;
  topic_id?: number | null;
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
  audio_status?: 'not_required' | 'processing' | 'ready' | 'failed' | null;
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
  input_type?: 'text' | 'audio' | null;
  requested_return_type?: 'auto' | 'text' | 'audio' | 'text_audio' | null;
  resolved_return_type?: 'text' | 'audio' | 'text_audio' | null;
  text_content?: string | null;
  audio_input_url?: string | null;
  audio_transcript?: string | null;
  answer_audio_url?: string | null;
  transcription_status?: 'not_required' | 'processing' | 'ready' | 'failed' | null;
  audio_status?: 'not_required' | 'processing' | 'ready' | 'failed' | null;
  audio_provider?: string | null;
  tts_model?: string | null;
  stt_model?: string | null;
  voice_id?: string | null;
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
  content?: string;
  audio?: Blob;
  audioFilename?: string;
  image?: File;
  file?: File;
  preferredResponseFormat?: PreferredResponseFormat;
  requestedReturnType?: 'auto' | 'text' | 'audio' | 'text_audio';
  language?: 'auto' | 'ar' | 'en';
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

export type StudyDayCode = 'sun' | 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat';

export interface StudyScheduleSession {
  type: 'lesson' | 'review';
  lesson_id?: number;
  title: string;
  chapter_id?: number | null;
  unit_id?: number | null;
  unit_number?: number | null;
  minutes: number;
  status: 'planned' | 'completed';
  completed: boolean;
  is_continuation?: boolean;
}

export interface StudyScheduleEntry {
  date: string;
  weekday: StudyDayCode;
  weekday_ar: string;
  planned_hours: number;
  planned_minutes: number;
  sessions: StudyScheduleSession[];
}

export interface StudyPlanSummary {
  start_date?: string;
  end_date?: string;
  exam_date?: string | null;
  total_lessons?: number;
  total_study_days?: number;
  weekly_hours?: number;
  hours_by_day?: Partial<Record<StudyDayCode, number>>;
  total_planned_minutes?: number;
  capacity_minutes?: number;
  over_capacity?: boolean;
  warnings?: string[];
}

export interface StudyPlan {
  id?: string;
  chapters: ChapterPlan[];
  weakTopics: string[];
  currentLesson: LessonItem;
  schedule?: StudyScheduleEntry[];
  summary?: StudyPlanSummary;
  config?: {
    title?: string;
    examDate?: string;
    startDate?: string;
    endDate?: string;
    studyDays?: StudyDayCode[];
    studyHoursByDay?: Partial<Record<StudyDayCode, number>>;
    lessonIds?: Array<string | number>;
    [key: string]: unknown;
  };
}

export type StudyPlanProgressStatus = 'not_started' | 'in_progress' | 'completed' | 'skipped' | 'overdue';
export type StudyPlanTrackStatus = 'ahead' | 'on_track' | 'behind';

export interface StudyPlanProgressNextLesson {
  id: number;
  title_ar: string;
  scheduled_date?: string | null;
  status: StudyPlanProgressStatus;
}

export interface StudyPlanUnitProgress {
  unit_id?: number | null;
  unit_title_ar: string;
  total_lessons: number;
  completed_lessons: number;
  completion_percent: number;
}

export interface StudyPlanScheduledLessonProgress {
  study_plan_item_id?: number | null;
  lesson_id: number;
  lesson_title_ar: string;
  unit_title_ar?: string | null;
  chapter_title_ar?: string | null;
  scheduled_date?: string | null;
  status: StudyPlanProgressStatus;
  completion_percent: number;
  estimated_minutes: number;
}

export interface StudyPlanProgress {
  plan_id: number | string;
  plan_title: string;
  total_scheduled_lessons: number;
  completed_lessons: number;
  in_progress_lessons: number;
  not_started_lessons: number;
  overdue_lessons: number;
  skipped_lessons?: number;
  completion_percent: number;
  expected_percent: number;
  track_status: StudyPlanTrackStatus;
  next_lesson?: StudyPlanProgressNextLesson | null;
  unit_progress: StudyPlanUnitProgress[];
  scheduled_lessons: StudyPlanScheduledLessonProgress[];
}

export interface FlashcardDeck {
  id: number;
  title: string;
  topic: string;
  count: number;
  mastered: number;
  cards: FlashcardItem[];
  titleAr?: string;
  descriptionAr?: string;
  scopeType?: string;
  scopeId?: string | null;
  status?: 'draft' | 'active' | 'archived' | string;
  source?: 'ai_generated' | 'manual' | 'book_rag' | string;
  totalCards?: number;
  dueCards?: number;
  newCards?: number;
  learningCards?: number;
  masteredCards?: number;
  overdueCards?: number;
  masteryPercent?: number;
  createdAt?: string;
  updatedAt?: string;
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
  topicId?: CurriculumEntityId | null;
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
  topicId?: string;
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

export type FlashcardCardType =
  | 'term_definition'
  | 'concept_explanation'
  | 'equation_law'
  | 'calculation'
  | 'experiment_result'
  | 'compare_contrast'
  | 'reaction_balancing'
  | 'safety_rule'
  | 'image_based'
  | 'definition'
  | 'formula'
  | 'term'
  | 'reaction'
  | 'comparison'
  | 'experiment'
  | 'common_mistake';

export type FlashcardRating = 'again' | 'hard' | 'good' | 'easy';
export type FlashcardReviewStatus = 'new' | 'learning' | 'review' | 'mastered' | 'suspended';

export type FlashcardGenerationConfig = {
  mode:
    | 'single_lesson'
    | 'selected_lessons'
    | 'chapter'
    | 'weak_lessons'
    | 'study_plan';
  lessonIds: CurriculumEntityId[];
  topicId?: CurriculumEntityId | null;
  topicIds?: CurriculumEntityId[];
  unitIds?: CurriculumEntityId[];
  cardsPerLesson: number;
  cardTypes: FlashcardCardType[];
  difficulty: 'easy' | 'medium' | 'hard' | 'mixed';
  includeSourcePage: boolean;
  spacedRepetitionEnabled: boolean;
};

export type GeneratedFlashcard = {
  id: string;
  deckId?: string | null;
  unitId?: string | null;
  chapterId: string | null;
  front: string;
  back: string;
  lessonId: string | null;
  topicId?: string | null;
  cardType: FlashcardCardType;
  difficulty: 'easy' | 'medium' | 'hard';
  sourcePage: number;
  sourcePageEnd?: number | null;
  sourceChunkId?: string;
  sourceChunkIds?: string[];
  descriptionAr?: string;
  technicalDescription?: string;
  hintAr?: string;
  explanationAr?: string;
  lessonTitleAr?: string;
  topicTitleAr?: string;
  unitTitleAr?: string;
  chapterTitleAr?: string;
  reviewState: 'new' | 'learning' | 'known' | 'review' | 'mastered' | 'suspended';
  repetitions?: number;
  lapses?: number;
  easeFactor?: number;
  intervalDays?: number;
  nextReviewAt?: string;
  dueAt?: string | null;
  lastReviewedAt?: string | null;
};

export interface FlashcardProgressSummary {
  totalCards: number;
  dueToday: number;
  newCards: number;
  learningCards: number;
  masteredCards: number;
  overdueCards: number;
  masteryPercent: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  title_ar?: string;
  body_ar?: string;
  type:
    | 'study_reminder'
    | 'quiz_due'
    | 'homework_feedback'
    | 'streak_warning'
    | 'achievement_unlocked'
    | 'exam_countdown'
    | 'overdue_lesson'
    | 'flashcards_due'
    | 'quiz_reminder'
    | 'weak_topic'
    | 'system'
    | 'exam'
    | 'lesson'
    | 'quiz';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'read' | 'unread' | 'archived';
  scheduled_at: string;
  sent_at?: string | null;
  read_at?: string | null;
  related_entity_type?: 'lesson' | 'quiz' | 'flashcard' | 'plan' | 'topic' | 'system';
  related_entity_id?: string;
  action_label?: string;
  action_url?: string;
}

export interface SemesterPlanConfig {
  startDate: string;
  endDate: string;
  studyDays: StudyDayCode[];
  studyHoursByDay?: Partial<Record<StudyDayCode, number>>;
  lessonDuration: string;
  weeklyRest: string;
  lessonIds: CurriculumEntityId[];
}

export interface ExamPlanConfig {
  title: string;
  examDate: string;
  dailyStudyHours: string;
  studyDays?: StudyDayCode[];
  studyHoursByDay?: Partial<Record<StudyDayCode, number>>;
  priority: string;
  lessonIds: CurriculumEntityId[];
}
