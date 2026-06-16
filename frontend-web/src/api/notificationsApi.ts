import { api } from './http';
import type { NotificationItem } from '../types';

export interface NotificationPreferenceItem {
  exam_reminders_enabled: boolean;
  lesson_reminders_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  in_app_enabled: boolean;
  reminder_time_local: string;
  timezone: string;
}

interface BackendNotification {
  id: string | number;
  title: string;
  message: string;
  type: NotificationItem['type'] | 'exam_reminder' | 'lesson_reminder';
  priority?: NotificationItem['priority'];
  status?: 'read' | 'unread' | 'archived';
  scheduled_for?: string;
  scheduled_at?: string;
  action_url?: string | null;
  metadata_json?: {
    source_type?: NotificationItem['related_entity_type'];
    source_id?: string | number;
  } | null;
}

const mapBackendNotification = (item: BackendNotification): NotificationItem => ({
  id: String(item.id),
  title: item.title,
  message: item.message,
  type: item.type === 'exam_reminder' ? 'exam' : item.type === 'lesson_reminder' ? 'lesson' : item.type,
  priority: item.priority === 'urgent' ? 'urgent' : item.priority === 'high' ? 'high' : item.priority === 'low' ? 'low' : 'normal',
  status: item.status === 'read' ? 'read' : 'unread',
  scheduled_at: item.scheduled_for || item.scheduled_at || new Date().toISOString(),
  action_url: item.action_url || undefined,
  related_entity_type: item.metadata_json?.source_type || undefined,
  related_entity_id: item.metadata_json?.source_id ? String(item.metadata_json.source_id) : undefined,
  action_label: item.action_url ? (item.type === 'exam_reminder' ? 'عرض خطة الامتحان' : 'ابدأ الدرس') : undefined
});

// Client-side local state mock fallback
let localNotifications: NotificationItem[] = [
  {
    id: 'notif-1',
    title: 'امتحان الكيمياء يقترب!',
    message: 'تبقت 13 يوماً على الامتحان النهائي. راجع خطة الامتحان الخاصة بك.',
    type: 'exam',
    priority: 'high',
    status: 'unread',
    scheduled_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    related_entity_type: 'plan',
    action_label: 'عرض خطة الامتحان',
    action_url: '/study-plan'
  },
  {
    id: 'notif-2',
    title: 'درس اليوم بانتظارك',
    message: 'حان وقت درس "الروابط التساهمية والأيونية". ابدأ الدراسة الآن لتحافظ على استمراريتك اليومية.',
    type: 'lesson',
    priority: 'normal',
    status: 'unread',
    scheduled_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    related_entity_type: 'lesson',
    related_entity_id: 'lesson_2_2',
    action_label: 'ابدأ الدرس',
    action_url: '/lessons/lesson_2_2'
  }
];

let localPreferences: NotificationPreferenceItem = {
  exam_reminders_enabled: true,
  lesson_reminders_enabled: true,
  push_enabled: true,
  email_enabled: false,
  in_app_enabled: true,
  reminder_time_local: '08:00',
  timezone: 'UTC'
};

export const notificationsApi = {
  async getNotifications(): Promise<NotificationItem[]> {
    try {
      const { data } = await api.get<BackendNotification[]>('/notifications');
      return data.map(mapBackendNotification);
    } catch {
      return [...localNotifications];
    }
  },

  async getUnreadCount(): Promise<{ unread_count: number }> {
    try {
      const { data } = await api.get<{ unread_count: number }>('/notifications/unread-count');
      return data;
    } catch {
      return {
        unread_count: localNotifications.filter((notification) => notification.status === 'unread').length
      };
    }
  },

  async markAsRead(id: string): Promise<NotificationItem | null> {
    try {
      const { data } = await api.patch<BackendNotification>(`/notifications/${id}/read`);
      return mapBackendNotification(data);
    } catch {
      localNotifications = localNotifications.map(n =>
        n.id === id ? { ...n, status: 'read' } : n
      );
      return localNotifications.find(n => n.id === id) || null;
    }
  },

  async markAllRead(): Promise<{ success: boolean }> {
    try {
      await api.post('/notifications/mark-all-read');
      return { success: true };
    } catch {
      try {
        await api.patch('/notifications/mark-all-read');
        return { success: true };
      } catch {
        localNotifications = localNotifications.map(n => ({ ...n, status: 'read' }));
        return { success: true };
      }
    }
  },

  async deleteNotification(id: string): Promise<{ success: boolean }> {
    try {
      await api.delete(`/notifications/${id}`);
      return { success: true };
    } catch {
      localNotifications = localNotifications.filter(n => n.id !== id);
      return { success: true };
    }
  },

  async getPreferences(): Promise<NotificationPreferenceItem> {
    try {
      const { data } = await api.get<NotificationPreferenceItem>('/notification-preferences');
      return data;
    } catch {
      return { ...localPreferences };
    }
  },

  async updatePreferences(updates: Partial<NotificationPreferenceItem>): Promise<NotificationPreferenceItem> {
    try {
      const { data } = await api.patch<NotificationPreferenceItem>('/notification-preferences', updates);
      localPreferences = { ...localPreferences, ...data };
      return data;
    } catch {
      localPreferences = { ...localPreferences, ...updates };
      return { ...localPreferences };
    }
  },

  async rebuildReminders(): Promise<{ success: boolean }> {
    try {
      await api.post('/reminders/rebuild');
      return { success: true };
    } catch {
      return { success: true };
    }
  }
};
