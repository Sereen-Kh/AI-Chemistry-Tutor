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

const AI_GENERATION_TIMEOUT_MS = 90000;

interface BackendChatSource {
  chunk_id: number;
  source_id: number;
  source?: string | null;
  source_type?: string | null;
  page_number?: number | null;
  printed_page_start?: number | null;
  printed_page_end?: number | null;
  content_type: string;
  content_preview?: string | null;
  unit_id?: string | number | null;
  lesson_id?: string | number | null;
  quality_status?: string | null;
  quality_warning?: string | null;
  reviewed_metadata_version?: string | null;
  curriculum_metadata?: Record<string, unknown> | null;
  similarity_score: number;
}

interface BackendChatAnswer {
  answer: string;
  answer_text?: string;
  answer_type: string;
  format?: string;
  audio_url?: string | null;
  audio_status?: AiAskResponse['audio_status'];
  route: string;
  grounding?: AiAskResponse['grounding'];
  external_sources?: AiAskResponse['external_sources'];
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

export const resolveMediaUrl = mediaUrl;

const asNumber = (value: unknown): number | undefined => (
  typeof value === 'number' && Number.isFinite(value) ? value : undefined
);

const asString = (value: unknown): string | undefined => (
  typeof value === 'string' ? value : undefined
);

const asId = (value: unknown): string | number | null | undefined => (
  (typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))) ? value : value === null ? null : undefined
);

const asRecord = (value: unknown): Record<string, unknown> | null | undefined => (
  value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : value === null ? null : undefined
);

const mapSourceRecord = (source: Record<string, unknown>): SourceCitation => ({
  title: asString(source.source) || asString(source.title) || 'كتاب الكيمياء - الصف التاسع',
  page: asNumber(source.printed_page_start) ?? asNumber(source.page_number) ?? asNumber(source.page) ?? null,
  chunk_id: asNumber(source.chunk_id) ?? asString(source.chunk_id) ?? 'unknown',
  quote: asString(source.content_preview) || asString(source.quote),
  content_type: asString(source.content_type),
  score: asNumber(source.similarity_score) ?? asNumber(source.score),
  source_type: asString(source.source_type),
  unit_id: asId(source.unit_id),
  lesson_id: asId(source.lesson_id),
  quality_status: asString(source.quality_status) ?? null,
  quality_warning: asString(source.quality_warning) ?? null,
  printed_page_start: asNumber(source.printed_page_start) ?? null,
  printed_page_end: asNumber(source.printed_page_end) ?? null,
  reviewed_metadata_version: asString(source.reviewed_metadata_version) ?? null,
  curriculum_metadata: asRecord(source.curriculum_metadata) ?? null,
});

const mapBackendAnswer = (request: AiAskRequest, response: BackendChatAnswer): AiAskResponse => {
  const backendSources = response.sources?.length ? response.sources : response.citations || [];
  const citations: SourceCitation[] = backendSources.map((source) => ({
    title: source.source || 'كتاب الكيمياء - الصف التاسع',
    page: source.printed_page_start ?? source.page_number ?? null,
    chunk_id: source.chunk_id,
    quote: source.content_preview || undefined,
    content_type: source.content_type,
    score: source.similarity_score,
    source_type: source.source_type ?? undefined,
    unit_id: source.unit_id,
    lesson_id: source.lesson_id,
    quality_status: source.quality_status ?? null,
    quality_warning: source.quality_warning ?? null,
    printed_page_start: source.printed_page_start ?? null,
    printed_page_end: source.printed_page_end ?? null,
    reviewed_metadata_version: source.reviewed_metadata_version ?? null,
    curriculum_metadata: source.curriculum_metadata ?? null,
  }));

  const result: AiAskResponse = {
    answer: response.answer_text || response.answer,
    sources: citations,
    citations,
    confidence: response.confidence,
    format: (response.format === 'text' || response.format === 'audio' || response.format === 'image' || response.format === 'video')
      ? response.format
      : request.answer_format,
    answer_type: response.answer_type,
    route: response.route,
    grounding: response.grounding,
    external_sources: response.external_sources || [],
    diagnostics: response.diagnostics,
    audio_status: response.audio_status,
    teaching_level: response.teaching_level,
    explanation_method: response.explanation_method,
    learning_modes: response.learning_modes,
    student_interests: response.student_interests,
    media_blocks: response.media_blocks,
  };

  const blocks = [...(response.blocks || []), ...(response.media_blocks || [])];
  const audioBlock = blocks.find((block) => block.type === 'audio' && block.url);
  const imageBlock = blocks.find((block) => ['image', 'source_page', 'source_image'].includes(block.type) && (block.image_url || block.url));
  if (response.audio_url) result.audio_url = mediaUrl(response.audio_url);
  if (!result.audio_url && audioBlock?.url) result.audio_url = mediaUrl(audioBlock.url);
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
    grounding: message.grounding || undefined,
    external_sources: message.external_sources || [],
    diagnostics: message.diagnostics,
    audio_status: message.audio_status,
    media_blocks: mediaBlocks,
  };

  const audioUrl = asString(audioBlock?.url);
  const answerAudioUrl = message.answer_audio_url || message.media_url || undefined;
  const imageUrl = asString(imageBlock?.image_url) || asString(imageBlock?.url);
  if (answerAudioUrl) response.audio_url = mediaUrl(answerAudioUrl);
  if (!response.audio_url && audioUrl) response.audio_url = mediaUrl(audioUrl);
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
    const formData = new FormData();
    formData.append('conversationId', String(sessionId));
    formData.append('requestedReturnType', request.requestedReturnType ?? (request.format === 'audio' ? 'audio' : 'auto'));
    formData.append('language', request.language ?? 'auto');
    formData.append('answerScope', request.answer_scope ?? 'auto');
    if (request.teaching_style) formData.append('teachingStyle', request.teaching_style);
    if (request.teaching_level) formData.append('teachingLevel', request.teaching_level);
    if (request.explanation_method) formData.append('explanationMethod', request.explanation_method);
    if (request.learning_modes?.length) formData.append('learningModes', request.learning_modes.join(','));
    if (request.student_interests?.length) formData.append('studentInterests', request.student_interests.join(','));
    if (request.action) formData.append('action', request.action);
    formData.append('webSearchRequested', String(request.webSearchRequested ?? false));
    if (request.audio) {
      formData.append('audio', request.audio, request.audioFilename ?? 'student-message.webm');
    } else if (request.content) {
      formData.append('text', request.content);
    }
    // Prepared for multimodal backend support. The current FastAPI endpoint
    // ignores undeclared multipart fields, so text/audio chat remains stable.
    if (request.image) formData.append('image', request.image, request.image.name);
    if (request.file) formData.append('file', request.file, request.file.name);
    if (request.preferredResponseFormat) formData.append('preferredResponseFormat', request.preferredResponseFormat);

    const { data } = await api.post<ChatMessageResponse>('/chat/messages', formData, {
      timeout: AI_GENERATION_TIMEOUT_MS,
    });
    return data;
  },

  async sendTextMessage(
    sessionId: number,
    text: string,
    request: Omit<SendSessionMessageRequest, 'content' | 'audio' | 'image' | 'file'> = {},
  ): Promise<ChatMessageResponse> {
    return this.sendSessionMessage(sessionId, { ...request, content: text });
  },

  async sendVoiceMessage(
    sessionId: number,
    audio: Blob,
    request: Omit<SendSessionMessageRequest, 'content' | 'audio' | 'image' | 'file'> = {},
  ): Promise<ChatMessageResponse> {
    return this.sendSessionMessage(sessionId, {
      ...request,
      audio,
      audioFilename: request.audioFilename ?? 'student-message.webm',
    });
  },

  async sendImageMessage(
    sessionId: number,
    image: File,
    text: string,
    request: Omit<SendSessionMessageRequest, 'content' | 'audio' | 'image' | 'file'> = {},
  ): Promise<ChatMessageResponse> {
    return this.sendSessionMessage(sessionId, { ...request, content: text, image });
  },

  async transcribeVoiceMessage(): Promise<never> {
    throw new Error('TRANSCRIBE_ENDPOINT_NOT_READY');
  },

  async generateResponseAudio(): Promise<never> {
    throw new Error('GENERATE_RESPONSE_AUDIO_ENDPOINT_NOT_READY');
  },

  async generateResponseImage(): Promise<never> {
    throw new Error('GENERATE_RESPONSE_IMAGE_ENDPOINT_NOT_READY');
  },

  async generateQuizFromAnswer(): Promise<never> {
    throw new Error('GENERATE_QUIZ_FROM_ANSWER_ENDPOINT_NOT_READY');
  },

  async generateFlashcardsFromAnswer(): Promise<never> {
    throw new Error('GENERATE_FLASHCARDS_FROM_ANSWER_ENDPOINT_NOT_READY');
  },

  async deleteSession(sessionId: number): Promise<void> {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  async ask(request: AiAskRequest): Promise<AiAskResponse> {
    try {
      const { data } = await api.post<BackendChatAnswer>('/ai/ask', {
        conversation_id: request.conversation_id,
        parent_message_id: request.parent_message_id,
        question: request.question,
        message: request.question,
        subject: request.subject,
        grade: request.grade,
        source_types: request.source_types,
        answer_format: request.answer_format,
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
        web_search_requested: request.web_search_requested ?? false,
        lesson_id: request.lesson_id,
        topic_id: request.topic_id,
      }, {
        timeout: AI_GENERATION_TIMEOUT_MS,
      });
      return mapBackendAnswer(request, data);
    } catch (error) {
      console.warn('Ask AI request failed', error);
      throw new Error('تعذر الوصول إلى معلّم الذكاء حالياً. تأكد أن الخادم يعمل ثم أعد المحاولة.', { cause: error });
    }
  },
};
