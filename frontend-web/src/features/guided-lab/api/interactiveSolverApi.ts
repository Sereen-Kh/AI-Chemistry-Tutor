import axios from 'axios';
import { api } from '../../../api/http';
import {
  buildMockGuidedSession,
  hclConcentrationProblem,
  mockAcceptedAnswers,
} from '../mockData';
import type {
  InteractiveSession,
  InteractiveSessionStatus,
  InteractiveStep,
  InteractiveStepStatus,
  SourceReference,
  StartInteractiveSessionRequest,
  SubmitStepAnswerRequest,
  SubmitStepAnswerResponse,
} from '../types';

interface BackendStep {
  id?: number;
  step_id?: number;
  step_index: number;
  step_key?: string;
  step_type?: string;
  prompt_ar?: string;
  prompt?: string;
  hint_ar?: string;
  hint?: string;
  status?: string;
  expected_answer?: string;
  explanation_ar?: string;
  explanation?: string;
}

interface BackendSource {
  chunk_id?: number | string;
  page_number?: number;
  page?: number;
  source_type?: string;
  content_type?: string;
  preview?: string;
  quote?: string;
  score?: number;
  similarity_score?: number;
  image_url?: string;
}

interface BackendSession {
  id?: number;
  session_id?: number;
  problem_text: string;
  problem_type?: string;
  status?: string;
  current_step_index?: number;
  current_step?: BackendStep | null;
  steps?: BackendStep[];
  source_chunks?: BackendSource[];
  sources?: BackendSource[];
  final_answer?: string;
  confidence_score?: number;
}

interface BackendAnswerResponse {
  is_correct: boolean;
  feedback_ar?: string;
  feedback?: string;
  misconception_type?: string;
  detected_error_type?: string;
  next_step?: BackendStep | null;
  current_step?: BackendStep | null;
  session_status?: string;
  final_answer?: string;
  final_summary?: {
    final_answer?: string;
    sources?: BackendSource[];
  } | null;
  sources?: BackendSource[];
}

interface BackendFinishSummary {
  session_id: number;
  status: InteractiveSessionStatus | string;
  final_answer: string;
  step_summary: Array<Record<string, unknown>>;
  sources?: BackendSource[];
  detected_weak_topics?: string[];
  suggested_mini_quiz_action?: Record<string, unknown>;
  suggested_flashcard_generation_action?: Record<string, unknown>;
}

const mockSessions = new Map<number, InteractiveSession>();

const canUseMockFallback = (): boolean =>
  import.meta.env.DEV || import.meta.env.VITE_GUIDED_LAB_MOCK === 'true';

const shouldFallbackToMock = (error: unknown): boolean => {
  if (!canUseMockFallback()) return false;
  if (!axios.isAxiosError(error)) return true;
  return !error.response || [404, 405, 501].includes(error.response.status);
};

const cloneSession = (session: InteractiveSession): InteractiveSession =>
  JSON.parse(JSON.stringify(session)) as InteractiveSession;

const normalizeStepStatus = (status?: string): InteractiveStepStatus => {
  if (status === 'completed' || status === 'correct') return 'correct';
  if (status === 'incorrect' || status === 'failed') return 'incorrect';
  if (status === 'skipped') return 'skipped';
  return 'pending';
};

const normalizeSessionStatus = (status?: string): InteractiveSessionStatus => {
  if (status === 'completed') return 'completed';
  if (status === 'abandoned') return 'abandoned';
  return 'active';
};

const mapSource = (source: BackendSource): SourceReference => ({
  chunk_id: Number(source.chunk_id ?? 0),
  page_number: source.page_number ?? source.page,
  source_type: source.source_type ?? 'textbook',
  content_type: source.content_type,
  preview: source.preview ?? source.quote,
  score: source.score ?? source.similarity_score,
  image_url: source.image_url,
});

const mapStep = (step: BackendStep): InteractiveStep => ({
  step_id: Number(step.step_id ?? step.id ?? step.step_index + 1),
  step_index: step.step_index,
  step_type: step.step_type ?? step.step_key ?? 'guided_step',
  prompt: step.prompt_ar ?? step.prompt ?? '',
  hint: step.hint_ar ?? step.hint,
  status: normalizeStepStatus(step.status),
  expected_answer: step.expected_answer,
  explanation: step.explanation_ar ?? step.explanation,
});

const mapSession = (session: BackendSession, mockMode = false): InteractiveSession => {
  const steps = (session.steps ?? []).map(mapStep);
  const currentStep = session.current_step ? mapStep(session.current_step) : steps[session.current_step_index ?? 0];
  return {
    session_id: Number(session.session_id ?? session.id ?? 0),
    problem_text: session.problem_text,
    problem_type: session.problem_type ?? 'guided_problem',
    status: normalizeSessionStatus(session.status),
    current_step_index: session.current_step_index ?? currentStep?.step_index ?? 0,
    current_step: currentStep,
    steps,
    sources: (session.sources ?? session.source_chunks ?? []).map(mapSource),
    final_answer: session.final_answer,
    confidence_score: session.confidence_score,
    mock_mode: mockMode,
  };
};

const getOrCreateMockSession = (sessionId: number): InteractiveSession => {
  const existing = mockSessions.get(sessionId);
  if (existing) return existing;
  const session = buildMockGuidedSession(hclConcentrationProblem, sessionId);
  mockSessions.set(sessionId, session);
  return session;
};

const normalizeAnswer = (value: string): string =>
  value
    .toLowerCase()
    .replace(/[أإآ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .replace(/×/g, 'x')
    .replace(/÷/g, '/')
    .replace(/,/g, '.')
    .replace(/\s+/g, '')
    .replace(/[()]/g, '');

const answerMatches = (stepId: number, answerText: string): boolean => {
  const normalized = normalizeAnswer(answerText);
  const accepted = mockAcceptedAnswers[stepId] ?? [];
  return accepted.some((answer) => {
    const expected = normalizeAnswer(answer);
    return normalized === expected || normalized.includes(expected);
  });
};

const mockSubmitStepAnswer = (
  sessionId: number,
  payload: SubmitStepAnswerRequest,
): SubmitStepAnswerResponse => {
  const session = getOrCreateMockSession(sessionId);
  const stepIndex = session.steps.findIndex((step) => step.step_id === payload.step_id);
  const currentIndex = stepIndex >= 0 ? stepIndex : session.current_step_index;
  const currentStep = session.steps[currentIndex];
  const isCorrect = answerMatches(currentStep.step_id, payload.answer_text);

  if (!isCorrect) {
    session.steps[currentIndex] = { ...currentStep, status: 'incorrect' };
    session.current_step = session.steps[currentIndex];
    mockSessions.set(sessionId, session);
    return {
      is_correct: false,
      feedback: 'الإجابة غير دقيقة بعد. راجع القانون والوحدة، ثم جرّب مرة أخرى.',
      detected_error_type: payload.answer_text.match(/100\s*ml/i) ? 'forgot_ml_to_l_conversion' : 'needs_retry',
      next_step: session.current_step,
      session_status: session.status,
      sources: session.sources,
    };
  }

  session.steps[currentIndex] = { ...currentStep, status: 'correct' };
  const nextStep = session.steps[currentIndex + 1];
  if (!nextStep) {
    session.status = 'completed';
    session.current_step_index = currentIndex;
    session.current_step = undefined;
    session.final_answer = 'Cg = 36.5 g/L، و C = 1 mol/L.';
  } else {
    session.current_step_index = nextStep.step_index;
    session.current_step = { ...nextStep, status: 'pending' };
  }
  mockSessions.set(sessionId, session);

  return {
    is_correct: true,
    feedback: currentStep.explanation ?? 'إجابة صحيحة. انتقل إلى الخطوة التالية.',
    next_step: session.current_step,
    session_status: session.status,
    final_answer: session.final_answer,
    sources: session.sources,
  };
};

const mapAnswerResponse = (response: BackendAnswerResponse): SubmitStepAnswerResponse => ({
  is_correct: response.is_correct,
  feedback: response.feedback_ar ?? response.feedback ?? '',
  detected_error_type: response.detected_error_type ?? response.misconception_type,
  next_step: response.next_step ? mapStep(response.next_step) : response.current_step ? mapStep(response.current_step) : undefined,
  session_status: normalizeSessionStatus(response.session_status),
  final_answer: response.final_answer ?? response.final_summary?.final_answer,
  sources: (response.sources ?? response.final_summary?.sources ?? []).map(mapSource),
});

export const interactiveSolverApi = {
  async startInteractiveSession(payload: StartInteractiveSessionRequest): Promise<InteractiveSession> {
    try {
      const { data } = await api.post<BackendSession>('/interactive-solver/sessions', payload);
      return mapSession(data);
    } catch (error) {
      if (!shouldFallbackToMock(error)) throw error;
      const session = buildMockGuidedSession(payload.problem_text, Date.now());
      mockSessions.set(session.session_id, session);
      return cloneSession(session);
    }
  },

  async getInteractiveSession(sessionId: number): Promise<InteractiveSession> {
    try {
      const { data } = await api.get<BackendSession>(`/interactive-solver/sessions/${sessionId}`);
      return mapSession(data);
    } catch (error) {
      if (!shouldFallbackToMock(error)) throw error;
      return cloneSession(getOrCreateMockSession(sessionId));
    }
  },

  async submitStepAnswer(
    sessionId: number,
    payload: SubmitStepAnswerRequest,
  ): Promise<SubmitStepAnswerResponse> {
    try {
      const { data } = await api.post<BackendAnswerResponse>(
        `/interactive-solver/sessions/${sessionId}/answer`,
        payload,
      );
      return mapAnswerResponse(data);
    } catch (error) {
      if (!shouldFallbackToMock(error)) throw error;
      return mockSubmitStepAnswer(sessionId, payload);
    }
  },

  async requestStepHint(sessionId: number, stepId: number): Promise<{ hint: string; mock_mode?: boolean }> {
    try {
      const { data } = await api.post<{ hint?: string; hint_ar?: string }>(
        `/interactive-solver/sessions/${sessionId}/hint`,
        { step_id: stepId },
      );
      return { hint: data.hint_ar ?? data.hint ?? 'راجع الخطوة السابقة وحاول مرة أخرى.' };
    } catch (error) {
      if (!shouldFallbackToMock(error)) throw error;
      const step = getOrCreateMockSession(sessionId).steps.find((item) => item.step_id === stepId);
      return { hint: step?.hint ?? 'استعمل القانون المناسب وانتبه للوحدات.', mock_mode: true };
    }
  },

  async finishInteractiveSession(sessionId: number): Promise<InteractiveSession> {
    try {
      const { data: summary } = await api.post<BackendFinishSummary>(`/interactive-solver/sessions/${sessionId}/finish`);
      const { data: refreshed } = await api.get<BackendSession>(`/interactive-solver/sessions/${sessionId}`);
      const session = mapSession(refreshed);
      return {
        ...session,
        status: normalizeSessionStatus(summary.status),
        final_answer: summary.final_answer || session.final_answer,
        sources: summary.sources?.length ? summary.sources.map(mapSource) : session.sources,
      };
    } catch (error) {
      if (!shouldFallbackToMock(error)) throw error;
      const session = getOrCreateMockSession(sessionId);
      session.status = 'completed';
      session.final_answer = session.final_answer ?? 'Cg = 36.5 g/L، و C = 1 mol/L.';
      session.steps = session.steps.map((step) => ({ ...step, status: step.status === 'incorrect' ? 'incorrect' : 'correct' }));
      mockSessions.set(sessionId, session);
      return cloneSession(session);
    }
  },
};
