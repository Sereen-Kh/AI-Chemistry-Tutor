import { useCallback, useEffect, useMemo, useState } from 'react';
import { notificationsApi } from '../api';
import type { NotificationItem } from '../types';

export const useNotifications = (limit = 8) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const list = await notificationsApi.getNotifications({ limit });
      setNotifications(list);
    } catch {
      setError('تعذر تحميل الإشعارات.');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh();
    }, 0);
    const handleUpdate = () => void refresh();
    window.addEventListener('notifications-updated', handleUpdate);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('notifications-updated', handleUpdate);
    };
  }, [refresh]);

  const unreadCount = useMemo(
    () => notifications.filter((notification) => notification.status === 'unread').length,
    [notifications],
  );

  const markAsRead = useCallback(async (id: string) => {
    await notificationsApi.markAsRead(id);
    setNotifications((current) => current.map((item) => (
      item.id === id ? { ...item, status: 'read' } : item
    )));
    window.dispatchEvent(new Event('notifications-updated'));
  }, []);

  const markAllRead = useCallback(async () => {
    await notificationsApi.markAllRead();
    setNotifications((current) => current.map((item) => ({ ...item, status: 'read' })));
    window.dispatchEvent(new Event('notifications-updated'));
  }, []);

  return {
    notifications,
    unreadCount,
    loading,
    error,
    refresh,
    markAsRead,
    markAllRead,
  };
};
