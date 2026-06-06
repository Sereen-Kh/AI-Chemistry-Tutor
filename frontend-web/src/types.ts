export type TeachingStyle = 'simple' | 'real_life' | 'visual' | 'exam';
export type AnswerFormat = 'text' | 'audio' | 'image' | 'video';
export type LessonStatus = 'completed' | 'current' | 'locked' | 'weak';

export interface UserPreferences {
  interests: string[];
  teachingStyle: TeachingStyle;
  answerFormat: AnswerFormat;
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
  teaching_style: TeachingStyle;
  interests: string[];
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
  sources: SourceCitation[];
  confidence: number;
  format: AnswerFormat;
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
  chapters: ChapterPlan[];
  weakTopics: string[];
  currentLesson: LessonItem;
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
