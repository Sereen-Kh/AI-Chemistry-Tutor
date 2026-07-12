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
  if (type === 'quiz') return 'quiz_due';
  if (type === 'quiz_reminder') return 'quiz_due';
  return type;
};

const actionLabelFor = (type: NotificationItem['type'], actionUrl?: string): string | undefined => {
  if (!actionUrl) return undefined;
  if (type === 'exam_countdown') return 'عرض خطة الامتحان';
  if (type === 'study_reminder' || type === 'overdue_lesson') return 'افتح الخطة';
  if (type === 'flashcards_due') return 'راجع البطاقات';
  if (type === 'weak_topic' || type === 'quiz_due') return 'ابدأ التدريب';
  if (type === 'homework_feedback') return 'راجع الملاحظات';
  if (type === 'achievement_unlocked') return 'عرض الإنجاز';
  if (type === 'streak_warning') return 'حافظ على السلسلة';
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

export const notificationsApi = {
  async getNotifications(query: NotificationQuery = {}): Promise<NotificationItem[]> {
    const { data } = await api.get<BackendNotification[]>('/notifications', { params: query });
    return data.map(mapBackendNotification);
  },

  async getUnreadCount(): Promise<{ unread_count: number }> {
    const { data } = await api.get<{ unread_count: number }>('/notifications/unread-count');
    return data;
  },

  async markAsRead(id: string): Promise<NotificationItem | null> {
    const { data } = await api.patch<BackendNotification>(`/notifications/${id}/read`);
    return mapBackendNotification(data);
  },

  async markAllRead(): Promise<{ success: boolean }> {
    try {
      await api.patch('/notifications/read-all');
      return { success: true };
    } catch {
      await api.patch('/notifications/mark-all-read');
      return { success: true };
    }
  },

  async deleteNotification(id: string): Promise<{ success: boolean }> {
    await api.delete(`/notifications/${id}`);
    return { success: true };
  },

  async getPreferences(): Promise<NotificationPreferenceItem> {
    try {
      const { data } = await api.get<NotificationPreferenceItem>('/users/me/notification-settings');
      return data;
    } catch {
      const { data } = await api.get<NotificationPreferenceItem>('/notification-preferences');
      return data;
    }
  },

  async updatePreferences(updates: Partial<NotificationPreferenceItem>): Promise<NotificationPreferenceItem> {
    try {
      const { data } = await api.patch<NotificationPreferenceItem>('/users/me/notification-settings', updates);
      return data;
    } catch {
      const { data } = await api.patch<NotificationPreferenceItem>('/notification-preferences', updates);
      return data;
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
    const { data } = await api.post<BackendNotification>('/notifications/test');
    return mapBackendNotification(data);
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
