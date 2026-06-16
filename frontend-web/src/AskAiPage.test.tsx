import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AskAiPage } from './App';
import { aiApi } from './api';
import type { ChatMessageResponse, ChatSessionResponse, UserPreferences } from './types';

vi.mock('./api', () => ({
  aiApi: {
    listSessions: vi.fn(),
    createSession: vi.fn(),
    getSession: vi.fn(),
    sendSessionMessage: vi.fn(),
    deleteSession: vi.fn(),
  },
  authApi: {},
  labApi: {},
  notificationsApi: {},
  userApi: {},
  toErrorMessage: (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback),
  messageResponseToAskResponse: (message: ChatMessageResponse) => ({
    answer: message.answer_text || message.content,
    sources: (message.sources || []).map((source) => ({
      title: String(source.source || 'كتاب الكيمياء - الصف التاسع'),
      page: Number(source.page_number || 0) || null,
      chunk_id: Number(source.chunk_id || 0),
      quote: String(source.content_type || ''),
      score: Number(source.similarity_score || 0),
    })),
    citations: [],
    confidence: message.confidence || 0,
    format: 'text',
    answer_type: message.answer_type || undefined,
    route: message.route || undefined,
    diagnostics: message.diagnostics,
  }),
}));

const mockedAiApi = vi.mocked(aiApi);

const preferences: UserPreferences = {
  interests: [],
  teachingStyle: 'real_life',
  answerFormat: 'text',
  teachingLevel: 'standard',
  explanationMethod: 'direct',
  learningModes: ['text'],
  studentInterests: [],
  language: 'ar',
  grade: 'grade_9',
  subject: 'chemistry',
};

const assistantMessage: ChatMessageResponse = {
  id: 2,
  session_id: 10,
  role: 'assistant',
  content: 'التركيز المولي يحسب بالعلاقة C = n / V.',
  answer_text: 'التركيز المولي يحسب بالعلاقة C = n / V.',
  format: 'text',
  confidence: 0.86,
  answer_type: 'text',
  route: 'textbook_rag',
  grounding: 'book',
  sources: [
    {
      chunk_id: 42,
      source_id: 7,
      source: 'syria_grade_9_chemistry',
      page_number: 11,
      content_type: 'definition',
      similarity_score: 0.86,
    },
  ],
  citations: [],
  blocks: [],
  media_blocks: [],
  source_blocks: [],
  page_numbers: [11],
  diagnostics: {},
  suggested_next_action: 'جرّب سؤالاً تدريبياً مرتبطاً بالمصدر.',
  created_at: new Date().toISOString(),
};

const buildSession = (messages: ChatMessageResponse[] = []): ChatSessionResponse => ({
  id: 10,
  user_id: 1,
  lesson_id: null,
  title: 'جلسة تركيز',
  style: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  messages,
});

const renderAskAi = () => {
  render(
    <MemoryRouter>
      <AskAiPage preferences={preferences} setPreferences={vi.fn()} />
    </MemoryRouter>,
  );
};

describe('AskAiPage persistent sessions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedAiApi.deleteSession.mockResolvedValue(undefined);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('loads chat sessions and renders persisted source evidence', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([
      {
        id: 1,
        session_id: 10,
        role: 'user',
        content: 'ما هو التركيز المولي؟',
        format: 'text',
        created_at: new Date().toISOString(),
      },
      assistantMessage,
    ])]);

    renderAskAi();

    expect((await screen.findAllByText('جلسة تركيز')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/التركيز المولي يحسب بالعلاقة/)).length).toBeGreaterThan(0);
    expect(screen.getByText('إجابة مدعومة بمصادر')).toBeInTheDocument();
    expect(screen.getByText('صفحة 11')).toBeInTheDocument();
  });

  it('creates a session on first send and posts through the session endpoint', async () => {
    const createdSession = buildSession();
    const userMessage: ChatMessageResponse = {
      id: 1,
      session_id: 10,
      role: 'user',
      content: 'ما هو التركيز المولي؟',
      format: 'text',
      created_at: new Date().toISOString(),
    };
    mockedAiApi.listSessions.mockResolvedValue([]);
    mockedAiApi.createSession.mockResolvedValue(createdSession);
    mockedAiApi.sendSessionMessage.mockResolvedValue(assistantMessage);
    mockedAiApi.getSession.mockResolvedValue(buildSession([userMessage, assistantMessage]));

    renderAskAi();

    const input = await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    await userEvent.type(input, 'ما هو التركيز المولي؟');
    await userEvent.click(screen.getByRole('button', { name: 'إرسال' }));

    await waitFor(() => {
      expect(mockedAiApi.createSession).toHaveBeenCalledWith({ title: 'ما هو التركيز المولي؟' });
      expect(mockedAiApi.sendSessionMessage).toHaveBeenCalledWith(10, expect.objectContaining({
        content: 'ما هو التركيز المولي؟',
        teaching_level: 'standard',
        explanation_method: 'direct',
        learning_modes: ['text'],
      }));
    });
    expect((await screen.findAllByText(/التركيز المولي يحسب بالعلاقة/)).length).toBeGreaterThan(0);
  });

  it('deletes a selected session from the history panel', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockedAiApi.listSessions.mockResolvedValue([buildSession()]);

    renderAskAi();

    expect((await screen.findAllByText('جلسة تركيز')).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByLabelText('حذف جلسة تركيز'));

    await waitFor(() => {
      expect(mockedAiApi.deleteSession).toHaveBeenCalledWith(10);
    });
  });
});
