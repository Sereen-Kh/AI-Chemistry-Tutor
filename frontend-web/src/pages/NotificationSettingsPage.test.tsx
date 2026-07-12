import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { notificationsApi } from '../api';
import { NotificationSettingsPage } from './NotificationSettingsPage';
import type { NotificationPreferenceItem } from '../api/notificationsApi';

vi.mock('../api', () => ({
  notificationsApi: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    sendTestNotification: vi.fn(),
  },
}));

const mockedNotificationsApi = vi.mocked(notificationsApi);

const preferences: NotificationPreferenceItem = {
  push_enabled: false,
  email_enabled: false,
  in_app_enabled: true,
  daily_study_reminder_enabled: true,
  daily_study_reminder_time: '08:00',
  exam_reminder_enabled: true,
  flashcards_reminder_enabled: true,
  overdue_lesson_reminder_enabled: true,
  weak_topic_reminder_enabled: true,
  quiet_hours_enabled: false,
  quiet_hours_start: '22:00',
  quiet_hours_end: '07:00',
  exam_reminders_enabled: true,
  lesson_reminders_enabled: true,
  reminder_time_local: '08:00',
  timezone: 'Asia/Damascus',
};

const renderSettings = () => {
  render(
    <MemoryRouter>
      <NotificationSettingsPage />
    </MemoryRouter>,
  );
};

describe('NotificationSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedNotificationsApi.getPreferences.mockResolvedValue(preferences);
    mockedNotificationsApi.updatePreferences.mockImplementation(async (updates) => ({
      ...preferences,
      ...updates,
    }));
    mockedNotificationsApi.sendTestNotification.mockResolvedValue({
      id: 'test-1',
      title: 'اختبار الإشعارات',
      message: 'هذه رسالة اختبار.',
      type: 'system',
      priority: 'normal',
      status: 'unread',
      scheduled_at: new Date().toISOString(),
    });
  });

  it('loads settings and updates an in-app preference', async () => {
    renderSettings();

    expect(await screen.findByText('إعدادات الإشعارات')).toBeInTheDocument();
    const inAppToggle = screen.getByLabelText(/داخل التطبيق/) as HTMLInputElement;
    expect(inAppToggle.checked).toBe(true);

    await userEvent.click(inAppToggle);

    await waitFor(() => {
      expect(mockedNotificationsApi.updatePreferences).toHaveBeenCalledWith({ in_app_enabled: false });
    });
    expect(await screen.findByText('تم حفظ الإعدادات.')).toBeInTheDocument();
  });

  it('renders an error state when settings cannot load', async () => {
    mockedNotificationsApi.getPreferences.mockRejectedValue(new Error('server down'));

    renderSettings();

    expect(await screen.findByText('تعذر تحميل إعدادات الإشعارات.')).toBeInTheDocument();
  });
});
