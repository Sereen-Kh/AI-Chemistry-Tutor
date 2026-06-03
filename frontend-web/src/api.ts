import axios from 'axios';

// By default in dev, the backend runs on localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const API_ORIGIN = API_BASE_URL.startsWith('http')
  ? new URL(API_BASE_URL).origin
  : window.location.origin;
const DEMO_EMAIL = 'rag_demo@example.com';
const DEMO_PASSWORD = 'password123';
const TOKEN_KEY = 'edumind_demo_token';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Types based on Swagger documentation
export interface Topic {
  id: number;
  title: string;
  description?: string;
  chapter_id: number;
}

export interface QuizQuestion {
  id: number;
  question_text: string;
  options: any;
  question_type: string;
}

export interface QuizGenerateResponse {
  questions: QuizQuestion[];
  recommendation_id?: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface ChatSource {
  chunk_id: number;
  source_id: number;
  source?: string | null;
  page_number?: number | null;
  content_type: string;
  similarity_score: number;
}

export type PreferredAnswerType = 'auto' | 'text' | 'image' | 'video' | 'mixed';
export type AnswerScope = 'auto' | 'book_only' | 'tutor_general';

export interface AnswerBlock {
  type: 'text' | 'equation' | 'table' | 'source_page' | 'image' | 'video_script' | 'clarification' | string;
  content: string;
  page?: number | null;
  image_url?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AnswerSourceBlock {
  book_id?: string | null;
  page?: number | null;
  chunk_id: number;
  chunk_type: string;
  score: number;
}

export interface ChatAnswer {
  answer: string;
  answer_type: string;
  route: string;
  grounding: string;
  answer_scope: AnswerScope;
  blocks: AnswerBlock[];
  sources: ChatSource[];
  source_blocks?: AnswerSourceBlock[];
  page_numbers: number[];
  confidence: number;
  diagnostics?: Record<string, unknown>;
  suggested_next_action?: string | null;
}

export const resolveMediaUrl = (url?: string | null): string => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `${API_ORIGIN}${url}`;
};

// API methods
export const getHealth = async (): Promise<HealthResponse> => {
  const { data } = await api.get('/health');
  return data;
};

export const getTopics = async (chapterId?: number): Promise<Topic[]> => {
  const { data } = await api.get('/topics', { params: { chapter_id: chapterId } });
  return data;
};

export const generateQuiz = async (topicId: number, limit: number = 5): Promise<QuizGenerateResponse> => {
  const { data } = await api.post('/quizzes/generate', {
    topic_id: topicId,
    source_type: 'topic',
    limit: limit
  });
  return data;
};

export const login = async (email = DEMO_EMAIL, password = DEMO_PASSWORD): Promise<string> => {
  const { data } = await api.post<LoginResponse>('/auth/login', { email, password });
  localStorage.setItem(TOKEN_KEY, data.access_token);
  return data.access_token;
};

export const ensureDemoToken = async (): Promise<string> => {
  const existing = localStorage.getItem(TOKEN_KEY);
  if (existing) {
    return existing;
  }

  try {
    await api.post('/auth/register', {
      email: DEMO_EMAIL,
      password: DEMO_PASSWORD,
      name: 'RAG Demo',
    });
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 400) {
      throw error;
    }
  }

  return login();
};

export const askChemistry = async (
  question: string,
  preferredAnswerType: PreferredAnswerType = 'auto',
  answerScope: AnswerScope = 'auto'
): Promise<ChatAnswer> => {
  await ensureDemoToken();
  try {
    const { data } = await api.post<ChatAnswer>('/chat/ask', {
      question,
      source_types: ['textbook'],
      preferred_answer_type: preferredAnswerType,
      answer_scope: answerScope,
    });
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      await ensureDemoToken();
      const { data } = await api.post<ChatAnswer>('/chat/ask', {
        question,
        source_types: ['textbook'],
        preferred_answer_type: preferredAnswerType,
        answer_scope: answerScope,
      });
      return data;
    }
    throw error;
  }
};
