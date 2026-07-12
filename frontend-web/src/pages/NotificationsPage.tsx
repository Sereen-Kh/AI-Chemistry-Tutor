import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationsApi } from '../api';
import { Button, ErrorBanner, LoadingSkeleton, PageHeader } from '../components/DesignSystem';
import { NotificationPermissionBanner } from '../components/notifications/NotificationPermissionBanner';
import type { NotificationItem } from '../types';

type NotificationFilter = 'all' | 'study' | 'exam' | 'flashcards' | 'system';
type NotificationGroup = 'today' | 'tomorrow' | 'this_week' | 'earlier';

const filterLabels: Array<{ key: NotificationFilter; label: string }> = [
  { key: 'all', label: 'الكل' },
  { key: 'study', label: 'الدراسة' },
  { key: 'exam', label: 'الاختبارات' },
  { key: 'flashcards', label: 'البطاقات' },
  { key: 'system', label: 'النظام' },
];

const filterTypes: Record<Exclude<NotificationFilter, 'all'>, NotificationItem['type'][]> = {
  study: ['study_reminder', 'overdue_lesson', 'weak_topic', 'streak_warning', 'lesson'],
  exam: ['exam_countdown', 'quiz_due', 'quiz_reminder', 'exam', 'quiz'],
  flashcards: ['flashcards_due'],
  system: ['system', 'homework_feedback', 'achievement_unlocked'],
};

const groupLabels: Record<NotificationGroup, string> = {
  today: 'اليوم',
  tomorrow: 'غداً',
  this_week: 'هذا الأسبوع',
  earlier: 'سابقاً',
};

const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());

const getNotificationGroup = (isoDate: string): NotificationGroup => {
  const now = startOfDay(new Date());
  const target = startOfDay(new Date(isoDate));
  const dayDiff = Math.round((target.getTime() - now.getTime()) / 86_400_000);
  if (dayDiff === 0) return 'today';
  if (dayDiff === 1) return 'tomorrow';
  if (dayDiff > 1 && dayDiff <= 7) return 'this_week';
  return 'earlier';
};

export const NotificationsPage = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeCategory, setActiveCategory] = useState<NotificationFilter>('all');

  const fetchNotifications = async () => {
    setLoading(true);
    setError('');
    try {
      const list = await notificationsApi.getNotifications();
      setNotifications(list);
    } catch (err) {
      console.error('Failed to load notifications', err);
      setError('تعذر تحميل التذكيرات. تحقق من اتصال الخادم ثم حاول مرة أخرى.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchNotifications();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const dispatchUpdate = () => {
    window.dispatchEvent(new Event('notifications-updated'));
  };

  const markRead = async (id: string) => {
    setError('');
    try {
      await notificationsApi.markAsRead(id);
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, status: 'read' as const } : n)
      );
      dispatchUpdate();
    } catch (err) {
      console.error(err);
      setError('تعذر تعليم التذكير كمقروء الآن.');
    }
  };

  const markAllRead = async () => {
    setError('');
    try {
      await notificationsApi.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, status: 'read' as const })));
      dispatchUpdate();
    } catch (err) {
      console.error(err);
      setError('تعذر تعليم كل التذكيرات كمقروءة الآن.');
    }
  };

  const deleteNotif = async (id: string) => {
    setError('');
    try {
      await notificationsApi.deleteNotification(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
      dispatchUpdate();
    } catch (err) {
      console.error(err);
      setError('تعذر حذف التذكير الآن.');
    }
  };

  const formatRelativeTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMins < 1) return 'الآن';
      if (diffMins < 60) return `منذ ${diffMins} دقيقة`;
      if (diffHours < 24) return `منذ ${diffHours} ساعة`;
      return `منذ ${diffDays} يوم`;
    } catch {
      return '';
    }
  };

  const getPriorityLabel = (priority: NotificationItem['priority']) => {
    switch (priority) {
      case 'urgent': return 'عاجل جداً';
      case 'high': return 'أولوية عالية';
      case 'normal': return 'عادي';
      case 'low': return 'منخفض';
    }
  };

  const getNotifIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'exam_countdown':
      case 'exam': return '🎯';
      case 'study_reminder':
      case 'overdue_lesson':
      case 'lesson': return '📖';
      case 'flashcards_due': return '▣';
      case 'weak_topic': return '!';
      case 'quiz_due':
      case 'quiz_reminder':
      case 'quiz': return '📝';
      case 'homework_feedback': return '✎';
      case 'streak_warning': return '🔥';
      case 'achievement_unlocked': return '★';
      case 'system': return '⚙️';
    }
  };

  const filteredNotifications = notifications.filter(n => {
    if (activeCategory === 'all') return true;
    return filterTypes[activeCategory].includes(n.type);
  });

  const groupedNotifications = filteredNotifications
    .slice()
    .sort((a, b) => new Date(b.scheduled_at).getTime() - new Date(a.scheduled_at).getTime())
    .reduce<Record<NotificationGroup, NotificationItem[]>>((groups, notification) => {
      groups[getNotificationGroup(notification.scheduled_at)].push(notification);
      return groups;
    }, { today: [], tomorrow: [], this_week: [], earlier: [] });

  const countForFilter = (filter: NotificationFilter) => {
    if (filter === 'all') return notifications.length;
    return notifications.filter(n => filterTypes[filter].includes(n.type)).length;
  };

  const unreadCount = notifications.filter(n => n.status === 'unread').length;
  const hasVisibleNotifications = Object.values(groupedNotifications).some(group => group.length > 0);

  return (
    <div className="page-stack notifications-page" dir="rtl">
      <PageHeader
        eyebrow="الإشعارات والتنبيهات"
        title="مركز الإشعارات الذكي"
        subtitle="تابع المواعيد الهامة وجداول المراجعة وتوصيات الذكاء الاصطناعي اليومية."
        action={
          <div className="notif-page-actions">
            {unreadCount > 0 && (
              <Button variant="ghost" onClick={markAllRead}>
                ✓ تحديد الكل كمقروء
              </Button>
            )}
            <Button variant="secondary" onClick={() => navigate('/notifications/settings')}>
              إعدادات الإشعارات
            </Button>
          </div>
        }
      />

      <NotificationPermissionBanner />

      {/* Tabs */}
      <div className="notif-filter-tabs">
        {filterLabels.map(cat => (
          <button
            key={cat.key}
            type="button"
            className={`notif-filter-tab ${activeCategory === cat.key ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat.key)}
            aria-pressed={activeCategory === cat.key}
          >
            {cat.label}
            {countForFilter(cat.key) > 0 && (
              <span style={{
                background: 'var(--bg4)',
                padding: '2px 6px',
                borderRadius: '8px',
                fontSize: '10px',
                color: 'var(--t2)'
              }}>{countForFilter(cat.key)}</span>
            )}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchNotifications} />}

      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : !hasVisibleNotifications ? (
        <div className="ed-card" style={{ textAlign: 'center', padding: '48px' }}>
          <div style={{ fontSize: '42px', marginBottom: '16px' }}>📭</div>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>لا توجد تذكيرات بعد</h2>
          <p style={{ color: 'var(--t2)', fontSize: '0.9rem' }}>خطة الدراسة تسير بشكل جيد، وسنظهر التذكيرات هنا عند توفرها.</p>
        </div>
      ) : (
        <div className="notif-group-list">
          {(['today', 'tomorrow', 'this_week', 'earlier'] as NotificationGroup[]).map(group => (
            groupedNotifications[group].length > 0 && (
              <section className="notif-group" key={group} aria-labelledby={`notif-group-${group}`}>
                <h2 id={`notif-group-${group}`}>{groupLabels[group]}</h2>
                <div className="notif-list">
                  {groupedNotifications[group].map(notif => (
                    <article
                      key={notif.id}
                      className={`notif-card ${notif.status === 'unread' ? 'unread' : ''}`}
                      aria-label={`${notif.status === 'unread' ? 'إشعار غير مقروء' : 'إشعار مقروء'}: ${notif.title}`}
                    >
                      <div className={`notif-icon-box ${notif.type}`}>
                        {getNotifIcon(notif.type)}
                      </div>
                      
                      <div className="notif-content">
                        <div className="notif-title-row">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <span className="notif-title">{notif.title}</span>
                            <span className={`notif-badge-priority ${notif.priority}`}>
                              {getPriorityLabel(notif.priority)}
                            </span>
                          </div>
                          <span className="notif-time">{formatRelativeTime(notif.scheduled_at)}</span>
                        </div>

                        <p className="notif-message">{notif.message}</p>
                        {(notif.related_entity_type || notif.related_entity_id) && (
                          <small className="notif-related">
                            {notif.related_entity_type ?? 'related'} · {notif.related_entity_id ?? '-'}
                          </small>
                        )}

                        <div className="notif-card-actions">
                          {notif.action_url && notif.action_label && (
                            <Button
                              variant={notif.status === 'unread' ? 'primary' : 'secondary'}
                              onClick={() => {
                                if (notif.status === 'unread') {
                                  void markRead(notif.id);
                                }
                                navigate(notif.action_url!);
                              }}
                              style={{ minHeight: '34px', padding: '0 12px', fontSize: '0.8rem' }}
                            >
                              {notif.action_label}
                            </Button>
                          )}
                          {notif.status === 'unread' && (
                            <Button
                              variant="ghost"
                              onClick={() => void markRead(notif.id)}
                              style={{ minHeight: '34px', padding: '0 12px', fontSize: '0.8rem' }}
                            >
                              ✓ مقروء
                            </Button>
                          )}
                          <button
                            type="button"
                            onClick={() => void deleteNotif(notif.id)}
                            className="notif-delete-btn"
                            aria-label={`حذف الإشعار: ${notif.title}`}
                          >
                            🗑️ حذف
                          </button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )
          ))}
        </div>
      )}
    </div>
  );
};
