import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { OnboardingPage } from './App';
import { authApi } from './api';
import type { InterestCategory, UserPreferences, UserProfile } from './types';

const interests: InterestCategory[] = [
  { id: 1, key: 'daily_life', name_ar: 'الحياة اليومية', icon: 'house' },
  { id: 2, key: 'laboratory', name_ar: 'المختبر', icon: 'flask-conical' },
  { id: 3, key: 'nature', name_ar: 'الطبيعة', icon: 'leaf' },
  { id: 4, key: 'cars', name_ar: 'السيارات', icon: 'car' },
];

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

const user: UserProfile = {
  id: 1,
  name: 'سارة',
  first_name: 'سارة',
  last_name: '',
  email: 'student@example.com',
  grade: 'grade_9',
  subject: 'chemistry',
  teaching_style: 'real_life_examples',
  answer_format: 'text',
  teaching_level: 'standard',
  explanation_method: 'direct',
  learning_modes: ['text'],
  student_interests: ['cars'],
  onboarding_completed: true,
  language: 'ar',
  xp: 0,
  level: 1,
  streak_days: 0,
};

const renderPage = (onSave = vi.fn()) => render(
  <MemoryRouter>
    <OnboardingPage preferences={preferences} onSave={onSave} />
  </MemoryRouter>,
);

describe('interest onboarding', () => {
  beforeEach(() => {
    vi.spyOn(authApi, 'interests').mockResolvedValue(interests);
    vi.spyOn(authApi, 'completeOnboarding').mockResolvedValue(user);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('requires one interest and sends stable keys without numeric ids', async () => {
    const onSave = vi.fn();
    renderPage(onSave);

    expect(await screen.findByText('ما الذي تحبّه؟')).toBeInTheDocument();
    const continueButton = screen.getByRole('button', { name: 'ابدأ التعلّم' });
    expect(continueButton).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'السيارات' }));
    expect(screen.getByText('1 من 3 محددة')).toBeInTheDocument();
    expect(continueButton).toBeEnabled();
    await userEvent.click(continueButton);

    await waitFor(() => {
      expect(authApi.completeOnboarding).toHaveBeenCalledWith(expect.objectContaining({
        studentInterests: ['cars'],
      }));
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({ studentInterests: ['cars'] }),
        user,
      );
    });
  });

  it('prevents selecting a fourth interest', async () => {
    renderPage();

    await screen.findByText('ما الذي تحبّه؟');
    await userEvent.click(screen.getByRole('button', { name: 'الحياة اليومية' }));
    await userEvent.click(screen.getByRole('button', { name: 'المختبر' }));
    await userEvent.click(screen.getByRole('button', { name: 'الطبيعة' }));
    await userEvent.click(screen.getByRole('button', { name: 'السيارات' }));

    expect(screen.getByText('3 من 3 محددة')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('يمكنك اختيار ثلاثة اهتمامات كحد أقصى.');
    expect(screen.getByRole('button', { name: 'السيارات' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('shows a retry state instead of static production interests', async () => {
    vi.mocked(authApi.interests)
      .mockRejectedValueOnce(new Error('تعذر تحميل الاهتمامات'))
      .mockResolvedValueOnce(interests);

    renderPage();

    expect(await screen.findByText('تعذر تحميل الاهتمامات')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'السيارات' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /إعادة المحاولة/ }));
    expect(await screen.findByRole('button', { name: 'السيارات' })).toBeInTheDocument();
  });
});
