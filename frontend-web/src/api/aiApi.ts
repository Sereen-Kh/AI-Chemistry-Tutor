import { api, API_BASE_URL } from './http';
import type {
  AiAskRequest,
  AiAskResponse,
  ChatMessageResponse,
  ChatSessionCreateRequest,
  ChatSessionResponse,
  SendSessionMessageRequest,
  SourceCitation,
} from '../types';

interface BackendChatSource {
  chunk_id: number;
  source_id: number;
  source?: string | null;
  page_number?: number | null;
  content_type: string;
  similarity_score: number;
}

interface BackendChatAnswer {
  answer: string;
  answer_text?: string;
  answer_type: string;
  route: string;
  blocks?: Array<{ type: string; content: string; url?: string | null; image_url?: string | null; page?: number | null; metadata?: Record<string, unknown> }>;
  sources: BackendChatSource[];
  citations?: BackendChatSource[];
  media_blocks?: Array<{ type: string; content: string; url?: string | null; image_url?: string | null; page?: number | null; metadata?: Record<string, unknown> }>;
  source_blocks?: Array<Record<string, unknown>>;
  page_numbers: number[];
  confidence: number;
  diagnostics?: Record<string, unknown>;
  suggested_next_action?: string | null;
  teaching_level?: AiAskResponse['teaching_level'];
  explanation_method?: AiAskResponse['explanation_method'];
  learning_modes?: AiAskResponse['learning_modes'];
  student_interests?: AiAskResponse['student_interests'];
}

const origin = API_BASE_URL.startsWith('http') ? new URL(API_BASE_URL).origin : window.location.origin;

const mediaUrl = (value?: string): string | undefined => {
  if (!value) return undefined;
  if (value.startsWith('http://') || value.startsWith('https://')) return value;
  return `${origin}${value}`;
};

const asNumber = (value: unknown): number | undefined => (
  typeof value === 'number' && Number.isFinite(value) ? value : undefined
);

const asString = (value: unknown): string | undefined => (
  typeof value === 'string' ? value : undefined
);

const mapSourceRecord = (source: Record<string, unknown>): SourceCitation => ({
  title: asString(source.source) || asString(source.title) || 'كتاب الكيمياء - الصف التاسع',
  page: asNumber(source.page_number) ?? asNumber(source.page) ?? null,
  chunk_id: asNumber(source.chunk_id) ?? asString(source.chunk_id) ?? 'unknown',
  quote: asString(source.content_type) || asString(source.quote),
  score: asNumber(source.similarity_score) ?? asNumber(source.score),
});

const mapBackendAnswer = (request: AiAskRequest, response: BackendChatAnswer): AiAskResponse => {
  const backendSources = response.sources?.length ? response.sources : response.citations || [];
  const citations: SourceCitation[] = backendSources.map((source) => ({
    title: source.source || 'كتاب الكيمياء - الصف التاسع',
    page: source.page_number ?? null,
    chunk_id: source.chunk_id,
    quote: source.content_type,
    score: source.similarity_score,
  }));

  const result: AiAskResponse = {
    answer: response.answer_text || response.answer,
    sources: citations,
    citations,
    confidence: response.confidence,
    format: request.answer_format,
    answer_type: response.answer_type,
    route: response.route,
    diagnostics: response.diagnostics,
    teaching_level: response.teaching_level,
    explanation_method: response.explanation_method,
    learning_modes: response.learning_modes,
    student_interests: response.student_interests,
    media_blocks: response.media_blocks,
  };

  const blocks = [...(response.blocks || []), ...(response.media_blocks || [])];
  const audioBlock = blocks.find((block) => block.type === 'audio' && block.url);
  const imageBlock = blocks.find((block) => ['image', 'source_page', 'source_image'].includes(block.type) && (block.image_url || block.url));
  if (audioBlock?.url) result.audio_url = mediaUrl(audioBlock.url);
  if (imageBlock?.image_url) result.source_page_image_url = mediaUrl(imageBlock.image_url);
  if (imageBlock?.url) result.source_page_image_url = mediaUrl(imageBlock.url);

  if (request.answer_format === 'image') {
    const firstPage = response.page_numbers[0] ?? citations[0]?.page;
    if (firstPage) {
      result.source_page_image_url = mediaUrl(`/media/books/syria_grade_9_chemistry/page_images/page_${String(firstPage).padStart(3, '0')}.png`);
    }
  }

  if (request.answer_format === 'video') {
    result.video_title = 'No suitable video found yet. Try text or image explanation.';
    result.video_source = 'internal';
  }

  return result;
};

export const messageResponseToAskResponse = (
  message: ChatMessageResponse,
  format: AiAskRequest['answer_format'] = 'text',
): AiAskResponse => {
  const sourceRecords = (
    message.sources?.length
      ? message.sources
      : message.citations?.length
        ? message.citations
        : []
  ) as Record<string, unknown>[];
  const citations = sourceRecords.map(mapSourceRecord);
  const mediaBlocks = message.media_blocks || [];
  const blocks = [...(message.blocks || []), ...mediaBlocks] as Record<string, unknown>[];
  const audioBlock = blocks.find((block) => block.type === 'audio' && block.url);
  const imageBlock = blocks.find((block) => (
    ['image', 'source_page', 'source_image'].includes(String(block.type)) && (block.image_url || block.url)
  ));
  const response: AiAskResponse = {
    answer: message.answer_text || message.content,
    answer_text: message.answer_text || message.content,
    sources: citations,
    citations,
    confidence: message.confidence ?? 0,
    format,
    answer_type: message.answer_type || undefined,
    route: message.route || undefined,
    diagnostics: message.diagnostics,
    media_blocks: mediaBlocks,
  };

  const audioUrl = asString(audioBlock?.url);
  const imageUrl = asString(imageBlock?.image_url) || asString(imageBlock?.url);
  if (audioUrl) response.audio_url = mediaUrl(audioUrl);
  if (imageUrl) response.source_page_image_url = mediaUrl(imageUrl);
  if (format === 'image' && !response.source_page_image_url) {
    const firstPage = message.page_numbers?.[0] ?? citations[0]?.page;
    if (firstPage) {
      response.source_page_image_url = mediaUrl(`/media/books/syria_grade_9_chemistry/page_images/page_${String(firstPage).padStart(3, '0')}.png`);
    }
  }
  if (format === 'video') {
    response.video_title = 'No suitable video found yet. Try text or image explanation.';
    response.video_source = 'internal';
  }
  return response;
};

export const aiApi = {
  async listSessions(): Promise<ChatSessionResponse[]> {
    const { data } = await api.get<ChatSessionResponse[]>('/chat/sessions');
    return data;
  },

  async createSession(request: ChatSessionCreateRequest = {}): Promise<ChatSessionResponse> {
    const { data } = await api.post<ChatSessionResponse>('/chat/sessions', request);
    return data;
  },

  async getSession(sessionId: number): Promise<ChatSessionResponse> {
    const { data } = await api.get<ChatSessionResponse>(`/chat/sessions/${sessionId}`);
    return data;
  },

  async sendSessionMessage(sessionId: number, request: SendSessionMessageRequest): Promise<ChatMessageResponse> {
    const { data } = await api.post<ChatMessageResponse>(`/chat/sessions/${sessionId}/messages`, {
      content: request.content,
      format: request.format ?? 'text',
      answer_scope: request.answer_scope ?? 'auto',
      source_types: request.source_types,
      teaching_style: request.teaching_style,
      teaching_level: request.teaching_level,
      explanation_method: request.explanation_method,
      learning_modes: request.learning_modes,
      student_interests: request.student_interests,
      action: request.action,
    });
    return data;
  },

  async deleteSession(sessionId: number): Promise<void> {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  async ask(request: AiAskRequest): Promise<AiAskResponse> {
    try {
      const { data } = await api.post<BackendChatAnswer>('/chat/ask', {
        conversation_id: request.conversation_id,
        parent_message_id: request.parent_message_id,
        question: request.question,
        message: request.question,
        source_types: request.source_types,
        preferred_answer_type: request.answer_format,
        answer_scope: request.answer_scope ?? 'auto',
        teaching_style: request.teaching_style,
        teaching_level: request.teaching_level,
        explanation_method: request.explanation_method,
        learning_modes: request.learning_modes,
        student_interests: request.student_interests,
        action: request.action,
        previous_question: request.previous_question,
        previous_answer: request.previous_answer,
        previous_sources: request.previous_sources,
        previous_selected_chunks: request.previous_selected_chunks,
      });
      return mapBackendAnswer(request, data);
    } catch (error) {
      console.warn('Ask AI request failed', error);
      throw new Error('تعذر الوصول إلى معلّم الذكاء حالياً. تأكد أن الخادم يعمل ثم أعد المحاولة.', { cause: error });
    }
  },
};
