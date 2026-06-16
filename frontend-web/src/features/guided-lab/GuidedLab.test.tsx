import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { interactiveSolverApi } from './api/interactiveSolverApi';
import { buildMockGuidedSession, hclConcentrationProblem } from './mockData';
import { GuidedLabPage } from './pages/GuidedLabPage';
import { SolverSessionPage } from './pages/SolverSessionPage';
import type { InteractiveSession } from './types';

vi.mock('./api/interactiveSolverApi', () => ({
  interactiveSolverApi: {
    startInteractiveSession: vi.fn(),
    getInteractiveSession: vi.fn(),
    submitStepAnswer: vi.fn(),
    requestStepHint: vi.fn(),
    finishInteractiveSession: vi.fn(),
  },
}));

const mockedApi = vi.mocked(interactiveSolverApi);

const renderGuidedLab = () => {
  render(
    <MemoryRouter initialEntries={['/guided-lab']}>
      <Routes>
        <Route path="/guided-lab" element={<GuidedLabPage />} />
        <Route path="/guided-lab/session/:sessionId" element={<div>Session route reached</div>} />
        <Route path="/lab" element={<div>Lab route</div>} />
      </Routes>
    </MemoryRouter>,
  );
};

const renderSolverSession = () => {
  render(
    <MemoryRouter initialEntries={['/guided-lab/session/123']}>
      <Routes>
        <Route path="/guided-lab/session/:sessionId" element={<SolverSessionPage />} />
        <Route path="/guided-lab" element={<div>Guided Lab route</div>} />
        <Route path="/lab" element={<div>Lab route</div>} />
        <Route path="/quizzes" element={<div>Quiz route</div>} />
        <Route path="/flashcards" element={<div>Flashcards route</div>} />
        <Route path="/ask-ai" element={<div>Ask AI route</div>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe('Guided Chemistry Problem Solver Lab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders the starter page and disables start for empty input', async () => {
    renderGuidedLab();

    expect(screen.getByText('حل مسائل الكيمياء الموجه')).toBeInTheDocument();
    const textarea = screen.getByLabelText('نص المسألة');
    await userEvent.clear(textarea);

    expect(screen.getByRole('button', { name: /ابدأ خطوة بخطوة/ })).toBeDisabled();
  });

  it('fills the textarea from an example problem card', async () => {
    renderGuidedLab();

    const textarea = screen.getByLabelText('نص المسألة');
    await userEvent.clear(textarea);
    await userEvent.click(screen.getByRole('button', { name: /مسألة تمديد/ }));

    expect((textarea as HTMLTextAreaElement).value).toContain('تركيزه 2 mol/L');
  });

  it('starts a mock-compatible session and navigates to the session route', async () => {
    mockedApi.startInteractiveSession.mockResolvedValue(buildMockGuidedSession(hclConcentrationProblem, 555));
    renderGuidedLab();

    await userEvent.click(screen.getByRole('button', { name: /ابدأ خطوة بخطوة/ }));

    expect(mockedApi.startInteractiveSession).toHaveBeenCalledWith({
      problem_text: hclConcentrationProblem,
      mode: 'guided',
    });
    expect(await screen.findByText('Session route reached')).toBeInTheDocument();
  });

  it('renders the current solver step and shows incorrect feedback without advancing', async () => {
    const session = buildMockGuidedSession(hclConcentrationProblem, 123);
    mockedApi.getInteractiveSession.mockResolvedValue(session);
    mockedApi.submitStepAnswer.mockResolvedValue({
      is_correct: false,
      feedback: 'الإجابة غير دقيقة بعد.',
      detected_error_type: 'needs_retry',
      next_step: session.current_step,
      session_status: 'active',
      sources: session.sources,
    });

    renderSolverSession();

    expect(await screen.findByText('ما القانون المناسب لحساب التركيز الغرامي Cg؟')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('إجابتك'), '100 mL');
    await userEvent.click(screen.getByRole('button', { name: /إرسال الإجابة/ }));

    expect(await screen.findByText('حاول مرة أخرى')).toBeInTheDocument();
    expect(screen.getByText('الإجابة غير دقيقة بعد.')).toBeInTheDocument();
  });

  it('shows success feedback for a correct answer and can render the final summary', async () => {
    let session: InteractiveSession = buildMockGuidedSession(hclConcentrationProblem, 123);
    const completedSession: InteractiveSession = {
      ...session,
      status: 'completed',
      current_step: undefined,
      final_answer: 'Cg = 36.5 g/L، و C = 1 mol/L.',
      steps: session.steps.map((step) => ({ ...step, status: 'correct' })),
    };
    mockedApi.getInteractiveSession.mockImplementation(async () => session);
    mockedApi.submitStepAnswer.mockImplementation(async () => {
      session = completedSession;
      return {
        is_correct: true,
        feedback: 'التركيز الغرامي يساوي كتلة المادة المنحلة مقسومة على حجم المحلول باللتر.',
        session_status: 'completed',
        final_answer: completedSession.final_answer,
        sources: completedSession.sources,
      };
    });
    mockedApi.finishInteractiveSession.mockResolvedValue(completedSession);

    renderSolverSession();

    expect(await screen.findByText('ما القانون المناسب لحساب التركيز الغرامي Cg؟')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('إجابتك'), 'Cg = m / V');
    await userEvent.click(screen.getByRole('button', { name: /إرسال الإجابة/ }));

    expect(await screen.findByText('إجابة صحيحة')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'ملخص الحل' })).toBeInTheDocument();
    });
    expect(screen.getAllByText(/36.5 g\/L/).length).toBeGreaterThan(0);
  });
});
