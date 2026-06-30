import { api } from './http';
import type { NotificationItem } from '../types';

export interface NotificationPreferenceItem {
  push_enabled: boolean;
  email_enabled: boolean;
  in_app_enabled: boolean;
  daily_study_reminder_enabled: boolean;
  daily_study_reminder_time: string;
  exam_reminder_enabled: boolean;
  flashcards_reminder_enabled: boolean;
  overdue_lesson_reminder_enabled: boolean;
  weak_topic_reminder_enabled: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  exam_reminders_enabled: boolean;
  lesson_reminders_enabled: boolean;
  reminder_time_local: string;
  timezone: string;
}

interface BackendNotification {
  id: string | number;
  title: string;
  message: string;
  title_ar?: string | null;
  body_ar?: string | null;
  type: NotificationItem['type'] | 'exam_reminder' | 'lesson_reminder';
  priority?: NotificationItem['priority'];
  status?: 'read' | 'unread' | 'archived';
  scheduled_for?: string;
  scheduled_at?: string;
  sent_at?: string | null;
  read_at?: string | null;
  action_url?: string | null;
  related_entity_type?: NotificationItem['related_entity_type'] | null;
  related_entity_id?: string | number | null;
  metadata_json?: {
    source_type?: NotificationItem['related_entity_type'];
    source_id?: string | number;
  } | null;
}

export interface PushTokenRequest {
  token: string;
  platform: 'web' | 'android' | 'ios' | 'expo';
  device_name?: string;
  browser?: string;
}

export interface PushTokenResponse extends PushTokenRequest {
  id: number;
  user_id: number;
  is_active: boolean;
  last_seen_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationQuery {
  status?: 'read' | 'unread' | 'archived';
  type?: NotificationItem['type'];
  limit?: number;
  offset?: number;
}

const normalizeType = (type: BackendNotification['type']): NotificationItem['type'] => {
  if (type === 'exam_reminder') return 'exam_countdown';
  if (type === 'lesson_reminder') return 'study_reminder';
  if (type === 'exam') return 'exam_countdown';
  if (type === 'lesson') return 'study_reminder';
  if (type === 'quiz') return 'quiz_reminder';
  return type;
};

const actionLabelFor = (type: NotificationItem['type'], actionUrl?: string): string | undefined => {
  if (!actionUrl) return undefined;
  if (type === 'exam_countdown') return 'عرض خطة الامتحان';
  if (type === 'study_reminder' || type === 'overdue_lesson') return 'افتح الخطة';
  if (type === 'flashcards_due') return 'راجع البطاقات';
  if (type === 'weak_topic' || type === 'quiz_reminder') return 'ابدأ التدريب';
  return 'فتح';
};

const mapBackendNotification = (item: BackendNotification): NotificationItem => ({
  id: String(item.id),
  title: item.title_ar || item.title,
  message: item.body_ar || item.message,
  title_ar: item.title_ar || item.title,
  body_ar: item.body_ar || item.message,
  type: normalizeType(item.type),
  priority: item.priority === 'urgent' ? 'urgent' : item.priority === 'high' ? 'high' : item.priority === 'low' ? 'low' : 'normal',
  status: item.status === 'archived' ? 'archived' : item.status === 'read' ? 'read' : 'unread',
  scheduled_at: item.scheduled_for || item.scheduled_at || new Date().toISOString(),
  sent_at: item.sent_at || null,
  read_at: item.read_at || null,
  action_url: item.action_url || undefined,
  related_entity_type: item.related_entity_type || item.metadata_json?.source_type || undefined,
  related_entity_id: item.related_entity_id ? String(item.related_entity_id) : item.metadata_json?.source_id ? String(item.metadata_json.source_id) : undefined,
  action_label: actionLabelFor(normalizeType(item.type), item.action_url || undefined)
});

// Client-side local state mock fallback
let localNotifications: NotificationItem[] = [
  {
    id: 'notif-1',
    title: 'امتحان الكيمياء يقترب!',
    message: 'تبقت 13 يوماً على الامتحان النهائي. راجع خطة الامتحان الخاصة بك.',
    type: 'exam_countdown',
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
    type: 'study_reminder',
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
  push_enabled: true,
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
  timezone: 'UTC'
};

export const notificationsApi = {
  async getNotifications(query: NotificationQuery = {}): Promise<NotificationItem[]> {
    try {
      const { data } = await api.get<BackendNotification[]>('/notifications', { params: query });
      return data.map(mapBackendNotification);
    } catch {
      return [...localNotifications].filter((notification) => {
        if (query.status && notification.status !== query.status) return false;
        if (query.type && notification.type !== query.type) return false;
        return true;
      }).slice(query.offset ?? 0, (query.offset ?? 0) + (query.limit ?? localNotifications.length));
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
  },

  async generateDueReminders(): Promise<{ success: boolean }> {
    try {
      await api.post('/notifications/generate-due');
      return { success: true };
    } catch {
      return { success: true };
    }
  },

  async sendTestNotification(): Promise<NotificationItem> {
    try {
      const { data } = await api.post<BackendNotification>('/notifications/test');
      return mapBackendNotification(data);
    } catch {
      const notification: NotificationItem = {
        id: `local-test-${Date.now()}`,
        title: 'اختبار الإشعارات',
        message: 'هذه رسالة اختبار محلية.',
        type: 'system',
        priority: 'normal',
        status: 'unread',
        scheduled_at: new Date().toISOString(),
        action_url: '/notifications',
        action_label: 'فتح',
      };
      localNotifications = [notification, ...localNotifications];
      return notification;
    }
  },

  async registerPushToken(request: PushTokenRequest): Promise<PushTokenResponse> {
    const { data } = await api.post<PushTokenResponse>('/push-tokens', request);
    return data;
  },

  async listPushTokens(): Promise<PushTokenResponse[]> {
    const { data } = await api.get<PushTokenResponse[]>('/push-tokens');
    return data;
  },

  async deletePushToken(id: number): Promise<void> {
    await api.delete(`/push-tokens/${id}`);
  }
};
