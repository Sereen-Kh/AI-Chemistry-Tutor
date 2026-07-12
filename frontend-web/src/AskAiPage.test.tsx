import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AskAiPage } from './pages/AskAIPage';
import { aiApi } from './api';
import { LearningModeSelector } from './components/DesignSystem';
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
  resolveMediaUrl: (value?: string) => value,
  toErrorMessage: (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback),
  messageResponseToAskResponse: (message: ChatMessageResponse) => {
    const format = ['text', 'audio', 'image', 'video'].includes(String(message.format))
      ? message.format
      : 'text';
    return {
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
      format,
      answer_type: message.answer_type || undefined,
      route: message.route || undefined,
      diagnostics: message.diagnostics,
      audio_url: message.answer_audio_url || message.media_url || undefined,
      audio_status: message.audio_status,
    };
  },
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
  return render(
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
    expect(screen.getAllByText('مصادر قوية').length).toBeGreaterThan(0);
    expect(screen.getByText('أفضل تطابق مع المصدر 86%')).toBeInTheDocument();
    expect(screen.getByText('صفحة 11')).toBeInTheDocument();
  });

  it('keeps answer confidence separate when no textbook source was retrieved', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([
      {
        id: 1,
        session_id: 10,
        role: 'user',
        content: 'ما هي الحموض؟',
        format: 'text',
        created_at: new Date().toISOString(),
      },
      {
        ...assistantMessage,
        id: 5,
        content: 'الحموض مواد تعطي أيونات الهدروجين في الماء.',
        answer_text: 'الحموض مواد تعطي أيونات الهدروجين في الماء.',
        confidence: 0.95,
        sources: [],
        citations: [],
        page_numbers: [],
      },
    ])]);

    renderAskAi();

    expect((await screen.findAllByText('لم أجد مصدراً كافياً في الكتاب')).length).toBeGreaterThan(0);
    expect(screen.getByText('ثقة الإجابة 95% · دون توثيق كتابي')).toBeInTheDocument();
    expect(screen.queryByText('ثقة المصدر 95%')).not.toBeInTheDocument();
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
        preferredResponseFormat: 'text',
      }));
    });
    expect((await screen.findAllByText(/التركيز المولي يحسب بالعلاقة/)).length).toBeGreaterThan(0);
  });

  it('uses one answer format and disables unsupported formats', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);

    renderAskAi();

    await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    expect(screen.queryByLabelText('اختيار نوع الإجابة')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /إعدادات الإجابة/ }));
    const textMode = screen.getByRole('radio', { name: 'صيغة الإجابة: نص' });
    const audioMode = screen.getByRole('radio', { name: 'صيغة الإجابة: صوت' });
    const shortVideoMode = screen.getByRole('radio', { name: 'صيغة الإجابة: فيديو قصير، قريباً' });

    expect(textMode).toHaveAttribute('aria-checked', 'true');
    expect(shortVideoMode).toBeDisabled();
    expect(screen.getAllByText('قريباً').length).toBeGreaterThan(0);

    await userEvent.click(audioMode);
    expect(textMode).toHaveAttribute('aria-checked', 'false');
    expect(audioMode).toHaveAttribute('aria-checked', 'true');
  });

  it('shows inline validation without calling backend for an empty composer', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);

    renderAskAi();

    await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    await userEvent.click(screen.getByRole('button', { name: 'إرسال' }));

    expect(await screen.findByText('اكتب سؤالاً أو أرفق صورة قبل الإرسال.')).toBeInTheDocument();
    expect(mockedAiApi.sendSessionMessage).not.toHaveBeenCalled();
  });

  it('maps backend Field required errors to Arabic composer feedback', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);
    mockedAiApi.createSession.mockResolvedValue(buildSession());
    mockedAiApi.sendSessionMessage.mockRejectedValue(new Error('Field required'));

    renderAskAi();

    const input = await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    await userEvent.type(input, 'ما هو الماء؟');
    await userEvent.click(screen.getByRole('button', { name: 'إرسال' }));

    expect(await screen.findByText('السؤال مطلوب')).toBeInTheDocument();
  });

  it('maps an expired session to an Arabic login message', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);
    mockedAiApi.createSession.mockResolvedValue(buildSession());
    mockedAiApi.sendSessionMessage.mockRejectedValue(new Error('Invalid or expired token'));

    renderAskAi();

    const input = await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    await userEvent.type(input, 'ما هو الماء؟');
    await userEvent.click(screen.getByRole('button', { name: 'إرسال' }));

    expect(await screen.findByText('انتهت صلاحية الجلسة. سجّل الدخول من جديد.')).toBeInTheDocument();
  });

  it('maps an unavailable backend to an Arabic retry message', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);
    mockedAiApi.createSession.mockResolvedValue(buildSession());
    mockedAiApi.sendSessionMessage.mockRejectedValue(new Error('Network Error'));

    renderAskAi();

    const input = await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    await userEvent.type(input, 'ما هو الماء؟');
    await userEvent.click(screen.getByRole('button', { name: 'إرسال' }));

    expect(
      await screen.findByText('تعذر الاتصال بالخادم. تأكد أن الخدمة تعمل ثم أعد المحاولة.'),
    ).toBeInTheDocument();
  });

  it('renders an audio player for audio answers', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([
      {
        id: 1,
        session_id: 10,
        role: 'user',
        content: 'ما هو الماء؟',
        format: 'text',
        created_at: new Date().toISOString(),
      },
      {
        ...assistantMessage,
        id: 3,
        format: 'audio',
        answer_audio_url: '/media/uploads/audio/output/answer_test.mp3',
        audio_status: 'ready',
      },
    ])]);

    const view = renderAskAi();

    expect((await screen.findAllByText(/التركيز المولي يحسب بالعلاقة/)).length).toBeGreaterThan(0);
    expect(view.container.querySelector('audio[src="/media/uploads/audio/output/answer_test.mp3"]')).toBeInTheDocument();
  });

  it('renders the transcript for a persisted student audio message', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([
      {
        id: 1,
        session_id: 10,
        role: 'user',
        content: 'ما هو التركيز المولي؟',
        format: 'audio',
        input_type: 'audio',
        audio_input_url: '/media/uploads/audio/input/student.webm',
        audio_transcript: 'ما هو التركيز المولي؟',
        transcription_status: 'ready',
        created_at: new Date().toISOString(),
      },
      assistantMessage,
    ])]);

    renderAskAi();

    expect(await screen.findByText(/النص المفرغ:/)).toBeInTheDocument();
    expect(screen.getAllByText(/ما هو التركيز المولي؟/).length).toBeGreaterThan(0);
  });

  it('renders failed audio state when TTS fails', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([
      {
        id: 1,
        session_id: 10,
        role: 'user',
        content: 'ما هو الماء؟',
        format: 'text',
        created_at: new Date().toISOString(),
      },
      {
        ...assistantMessage,
        id: 4,
        format: 'audio',
        answer_audio_url: null,
        audio_status: 'failed',
      },
    ])]);

    renderAskAi();

    expect(await screen.findByText('تعذر توليد الصوت. الإجابة النصية متاحة.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'أعد المحاولة' })).toBeInTheDocument();
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

describe('LearningModeSelector compatibility', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('keeps legacy multi-select behavior by default', async () => {
    const onChange = vi.fn();
    render(<LearningModeSelector value={['text']} onChange={onChange} />);

    await userEvent.click(screen.getByRole('button', { name: /نمط التعلم: صوت/ }));

    expect(onChange).toHaveBeenCalledWith(['text', 'audio']);
  });

  it('can opt into single-select behavior', async () => {
    const onChange = vi.fn();
    render(<LearningModeSelector value={['text']} onChange={onChange} singleSelect />);

    await userEvent.click(screen.getByRole('radio', { name: /نمط التعلم: صوت/ }));

    expect(onChange).toHaveBeenCalledWith(['audio']);
  });
});
