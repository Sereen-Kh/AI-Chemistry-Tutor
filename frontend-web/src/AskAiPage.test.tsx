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
        quote: String(source.content_preview || ''),
        content_type: String(source.content_type || ''),
        score: Number(source.similarity_score || 0),
      })),
      citations: [],
      confidence: message.confidence || 0,
      format,
      answer_type: message.answer_type || undefined,
      route: message.route || undefined,
      grounding: message.grounding || undefined,
      external_sources: message.external_sources || [],
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
  learningMemoryEnabled: true,
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
      content_preview: 'التركيز المولي هو عدد مولات المادة المذابة في حجم المحلول.',
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
    const sourceSummary = screen.getByText('من الكتاب · مصدر واحد');
    expect(sourceSummary.closest('details')).not.toHaveAttribute('open');
    expect(screen.getByText('أفضل تطابق مع المصدر 86%')).toBeInTheDocument();
    await userEvent.click(sourceSummary);
    expect(screen.getByText('صفحة 11')).toBeInTheDocument();
    expect(screen.getByText('التركيز المولي هو عدد مولات المادة المذابة في حجم المحلول.')).toBeInTheDocument();
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

    expect((await screen.findAllByText('دون مصدر كتابي')).length).toBe(1);
    expect(screen.queryByText('المصادر من الكتاب')).not.toBeInTheDocument();
    expect(screen.queryByText('ثقة المصدر 95%')).not.toBeInTheDocument();
  });

  it('uses an explicit insufficient-evidence message only for not-found answers', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([
      {
        id: 1,
        session_id: 10,
        role: 'user',
        content: 'سؤال خارج نطاق الكتاب',
        format: 'text',
        created_at: new Date().toISOString(),
      },
      {
        ...assistantMessage,
        id: 6,
        content: 'لم أجد معلومات كافية في المصادر المراجعة.',
        answer_text: 'لم أجد معلومات كافية في المصادر المراجعة.',
        confidence: 0.08,
        answer_type: 'not_found',
        route: 'not_found',
        sources: [],
        citations: [],
        page_numbers: [],
      },
    ])]);

    renderAskAi();

    expect((await screen.findAllByText('دون مصدر كتابي')).length).toBe(1);
  });

  it('renders assistant Markdown without exposing raw HTML', async () => {
    const markdownMessage = {
      ...assistantMessage,
      content: '**الماء** مركب كيميائي.\n\n- H2O\n- NaCl\n\n<script>alert("x")</script>',
      answer_text: '**الماء** مركب كيميائي.\n\n- H2O\n- NaCl\n\n<script>alert("x")</script>',
    };
    mockedAiApi.listSessions.mockResolvedValue([buildSession([markdownMessage])]);

    const view = renderAskAi();

    const boldText = await screen.findByText('الماء');
    expect(boldText.closest('strong')).toBeInTheDocument();
    expect(view.container.textContent).not.toContain('**');
    expect(view.container.querySelector('script')).not.toBeInTheDocument();
    expect(view.container.textContent).not.toContain('alert("x")');
    expect(screen.getByText('H2O')).toHaveClass('chem-formula');
  });

  it('renders external sources separately from textbook sources', async () => {
    mockedAiApi.listSessions.mockResolvedValue([buildSession([{
      ...assistantMessage,
      sources: [],
      citations: [],
      grounding: 'web',
      external_sources: [{
        title: 'مصدر علمي خارجي',
        url: 'https://example.org/water',
        domain: 'example.org',
        cited_text: 'Water is used in cooling.',
      }],
    }])]);

    renderAskAi();

    const summary = await screen.findByText('مصادر خارجية · مصدر واحد');
    expect(summary.closest('details')).not.toHaveAttribute('open');
    expect(screen.queryByText('دون مصدر كتابي')).not.toBeInTheDocument();
    await userEvent.click(summary);
    expect(screen.getByRole('link', { name: 'فتح المصدر' })).toHaveAttribute(
      'href',
      'https://example.org/water',
    );
  });

  it('requests web grounding only after the student clicks the fallback action', async () => {
    const noSourceMessage = {
      ...assistantMessage,
      sources: [],
      citations: [],
      confidence: 0.1,
      route: 'not_found',
    };
    const webMessage = {
      ...noSourceMessage,
      id: 9,
      grounding: 'web',
      external_sources: [{
        title: 'مصدر خارجي',
        url: 'https://example.org/source',
        domain: 'example.org',
        cited_text: 'Grounded text.',
      }],
    };
    mockedAiApi.listSessions.mockResolvedValue([buildSession([noSourceMessage])]);
    mockedAiApi.sendSessionMessage.mockResolvedValue(webMessage);
    mockedAiApi.getSession.mockResolvedValue(buildSession([noSourceMessage, webMessage]));

    renderAskAi();
    await userEvent.click(await screen.findByRole('button', { name: 'ابحث في مصادر ويب' }));

    await waitFor(() => {
      expect(mockedAiApi.sendSessionMessage).toHaveBeenCalledWith(10, expect.objectContaining({
        webSearchRequested: true,
      }));
    });
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

  it('keeps response formats and advanced dropdowns out of the student interface', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);

    renderAskAi();

    await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    expect(screen.queryByLabelText('اختيار نوع الإجابة')).not.toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /غيّر أسلوب الشرح/ }));
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /مختصر وواضح/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /علّمني خطوة بخطوة/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /من الكتاب فقط/ })).toBeInTheDocument();
  });

  it('lets the student apply a guided explanation preset before sending', async () => {
    mockedAiApi.listSessions.mockResolvedValue([]);
    mockedAiApi.createSession.mockResolvedValue(buildSession());
    mockedAiApi.sendSessionMessage.mockResolvedValue(assistantMessage);
    mockedAiApi.getSession.mockResolvedValue(buildSession([assistantMessage]));

    renderAskAi();

    await screen.findByLabelText('سؤال للذكاء الاصطناعي');
    await userEvent.click(screen.getByRole('button', { name: /غيّر أسلوب الشرح/ }));
    const guidedPreset = screen.getByRole('button', { name: /علّمني خطوة بخطوة/ });
    await userEvent.click(guidedPreset);
    expect(guidedPreset).toHaveAttribute('aria-pressed', 'true');

    await userEvent.type(screen.getByLabelText('سؤال للذكاء الاصطناعي'), 'اشرح التركيز المولي');
    await userEvent.click(screen.getByRole('button', { name: 'إرسال' }));

    await waitFor(() => {
      expect(mockedAiApi.sendSessionMessage).toHaveBeenCalledWith(10, expect.objectContaining({
        teaching_level: 'standard',
        explanation_method: 'step_by_step',
        answer_scope: 'auto',
      }));
    });
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
