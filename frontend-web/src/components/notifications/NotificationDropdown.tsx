import { Link, useNavigate } from 'react-router-dom';
import { Button, LoadingSkeleton } from '../DesignSystem';
import type { NotificationItem } from '../../types';

const typeLabel: Record<NotificationItem['type'], string> = {
  study_reminder: 'الدراسة',
  quiz_due: 'اختبار قصير',
  homework_feedback: 'واجب',
  streak_warning: 'استمرارية',
  achievement_unlocked: 'إنجاز',
  exam_countdown: 'اختبار',
  overdue_lesson: 'متأخر',
  flashcards_due: 'بطاقات',
  quiz_reminder: 'اختبار قصير',
  weak_topic: 'نقطة ضعف',
  system: 'النظام',
  exam: 'اختبار',
  lesson: 'الدراسة',
  quiz: 'اختبار',
};

const iconFor = (type: NotificationItem['type']): string => {
  if (type === 'exam_countdown' || type === 'exam') return '🎯';
  if (type === 'flashcards_due') return '▣';
  if (type === 'weak_topic') return '!';
  if (type === 'quiz_due' || type === 'quiz_reminder' || type === 'quiz') return '📝';
  if (type === 'homework_feedback') return '✎';
  if (type === 'streak_warning') return '🔥';
  if (type === 'achievement_unlocked') return '★';
  if (type === 'system') return '⚙';
  return '📘';
};

const relativeTime = (iso: string): string => {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(0, Math.floor(diff / 60000));
  if (minutes < 1) return 'الآن';
  if (minutes < 60) return `منذ ${minutes} د`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `منذ ${hours} س`;
  return `منذ ${Math.floor(hours / 24)} يوم`;
};

export const NotificationDropdown = ({
  notifications,
  loading,
  onMarkRead,
  onMarkAllRead,
  onClose,
}: {
  notifications: NotificationItem[];
  loading: boolean;
  onMarkRead: (id: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onClose: () => void;
}) => {
  const navigate = useNavigate();
  const latest = notifications.slice(0, 6);
  const unread = notifications.some((item) => item.status === 'unread');

  return (
    <div className="notification-dropdown" role="dialog" aria-label="آخر الإشعارات">
      <div className="notification-dropdown-head">
        <div>
          <strong>الإشعارات</strong>
          <span>{unread ? 'لديك تذكيرات غير مقروءة' : 'كل شيء مقروء'}</span>
        </div>
        {unread && (
          <Button variant="ghost" className="ed-btn-xs" onClick={() => void onMarkAllRead()}>
            تحديد الكل
          </Button>
        )}
      </div>
      {loading ? (
        <LoadingSkeleton rows={3} />
      ) : latest.length ? (
        <div className="notification-dropdown-list">
          {latest.map((notification) => (
            <button
              key={notification.id}
              type="button"
              className={notification.status === 'unread' ? 'notification-dropdown-item unread' : 'notification-dropdown-item'}
              onClick={async () => {
                if (notification.status === 'unread') await onMarkRead(notification.id);
                onClose();
                navigate(notification.action_url || '/notifications');
              }}
            >
              <span className="notification-dropdown-icon">{iconFor(notification.type)}</span>
              <span>
                <strong>{notification.title}</strong>
                <small>{notification.message}</small>
                <em>{typeLabel[notification.type]} · {relativeTime(notification.scheduled_at)}</em>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="notification-dropdown-empty">
          <strong>لا توجد إشعارات</strong>
          <span>سنرسل تذكيرات الدراسة والمراجعة هنا.</span>
        </div>
      )}
      <div className="notification-dropdown-foot">
        <Link to="/notifications" onClick={onClose}>عرض كل الإشعارات</Link>
        <Link to="/notifications/settings" onClick={onClose}>الإعدادات</Link>
      </div>
    </div>
  );
};
