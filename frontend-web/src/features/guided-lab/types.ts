export type InteractiveSessionStatus = 'active' | 'completed' | 'abandoned';

export type InteractiveStepStatus = 'pending' | 'correct' | 'incorrect' | 'skipped';

export interface SourceReference {
  chunk_id: number;
  page_number?: number;
  source_type: 'textbook' | 'solution_book' | 'exam' | string;
  content_type?: string;
  preview?: string;
  score?: number;
  image_url?: string;
}

export interface InteractiveStep {
  step_id: number;
  step_index: number;
  step_type: string;
  prompt: string;
  hint?: string;
  status: InteractiveStepStatus;
  expected_answer?: string;
  explanation?: string;
}

export interface InteractiveSession {
  session_id: number;
  problem_text: string;
  problem_type: string;
  status: InteractiveSessionStatus;
  current_step_index: number;
  current_step?: InteractiveStep;
  steps: InteractiveStep[];
  sources: SourceReference[];
  final_answer?: string;
  confidence_score?: number;
  mock_mode?: boolean;
}

export interface StartInteractiveSessionRequest {
  problem_text: string;
  topic_id?: number;
  lesson_id?: number;
  mode?: 'guided' | 'practice';
}

export interface SubmitStepAnswerRequest {
  step_id: number;
  answer_text: string;
}

export interface SubmitStepAnswerResponse {
  is_correct: boolean;
  feedback: string;
  detected_error_type?: string;
  next_step?: InteractiveStep;
  session_status: InteractiveSessionStatus;
  final_answer?: string;
  sources?: SourceReference[];
}

export interface InteractiveSessionSummary {
  final_answer: string;
  completed_steps: InteractiveStep[];
  sources: SourceReference[];
  detected_weak_topics: string[];
  mini_quiz_label: string;
  flashcards_label: string;
}
