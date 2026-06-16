import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { notificationsApi } from '../api';
import { NotificationsPage } from './NotificationsPage';
import type { NotificationItem } from '../types';

vi.mock('../api', () => ({
  notificationsApi: {
    getNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllRead: vi.fn(),
    deleteNotification: vi.fn(),
  },
}));

const mockedNotificationsApi = vi.mocked(notificationsApi);

const scheduledAt = (daysFromNow: number): string => {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  return date.toISOString();
};

const renderNotificationsPage = () => {
  render(
    <MemoryRouter>
      <NotificationsPage />
    </MemoryRouter>
  );
};

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedNotificationsApi.markAsRead.mockResolvedValue(null);
    mockedNotificationsApi.markAllRead.mockResolvedValue({ success: true });
    mockedNotificationsApi.deleteNotification.mockResolvedValue({ success: true });
  });

  it('renders grouped reminder notifications and filters unread items', async () => {
    const notifications: NotificationItem[] = [
      {
        id: 'exam-1',
        type: 'exam',
        title: 'امتحان قريب',
        message: 'راجع خطة الامتحان قبل الموعد.',
        priority: 'high',
        status: 'unread',
        scheduled_at: scheduledAt(0),
        action_label: 'عرض الخطة',
        action_url: '/study-plan',
      },
      {
        id: 'lesson-1',
        type: 'lesson',
        title: 'درس الغد',
        message: 'لديك درس مجدول غداً.',
        priority: 'normal',
        status: 'read',
        scheduled_at: scheduledAt(1),
        action_label: 'ابدأ الدرس',
        action_url: '/lessons/1',
      },
    ];
    mockedNotificationsApi.getNotifications.mockResolvedValue(notifications);

    renderNotificationsPage();

    expect(await screen.findByText('امتحان قريب')).toBeInTheDocument();
    expect(screen.getByText('اليوم')).toBeInTheDocument();
    expect(screen.getByText('غداً')).toBeInTheDocument();
    expect(screen.getByText('درس الغد')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /غير مقروءة/ }));

    expect(screen.getByText('امتحان قريب')).toBeInTheDocument();
    expect(screen.queryByText('درس الغد')).not.toBeInTheDocument();
  });

  it('marks a single notification as read', async () => {
    mockedNotificationsApi.getNotifications.mockResolvedValue([
      {
        id: 'lesson-2',
        type: 'lesson',
        title: 'موعد الدرس الآن',
        message: 'ابدأ درس الكيمياء الآن.',
        priority: 'normal',
        status: 'unread',
        scheduled_at: scheduledAt(0),
      },
    ]);

    renderNotificationsPage();

    const card = await screen.findByText('موعد الدرس الآن');
    const notificationCard = card.closest('.notif-card');
    expect(notificationCard).not.toBeNull();

    await userEvent.click(within(notificationCard as HTMLElement).getByRole('button', { name: /مقروء/ }));

    await waitFor(() => {
      expect(mockedNotificationsApi.markAsRead).toHaveBeenCalledWith('lesson-2');
    });
  });

  it('renders the requested empty reminder state', async () => {
    mockedNotificationsApi.getNotifications.mockResolvedValue([]);

    renderNotificationsPage();

    expect(await screen.findByText('لا توجد تذكيرات بعد')).toBeInTheDocument();
    expect(screen.getByText('خطة الدراسة تسير بشكل جيد، وسنظهر التذكيرات هنا عند توفرها.')).toBeInTheDocument();
  });
});
