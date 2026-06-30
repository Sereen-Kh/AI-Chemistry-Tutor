import { useEffect, useRef, useState } from 'react';
import { useNotifications } from '../../hooks/useNotifications';
import { NotificationDropdown } from './NotificationDropdown';

export const NotificationBell = ({ onUnreadChange }: { onUnreadChange?: (count: number) => void }) => {
  const [open, setOpen] = useState(false);
  const launcherRef = useRef<HTMLButtonElement | null>(null);
  const { notifications, unreadCount, loading, markAsRead, markAllRead } = useNotifications(8);

  useEffect(() => {
    onUnreadChange?.(unreadCount);
  }, [onUnreadChange, unreadCount]);

  useEffect(() => {
    if (!open) return undefined;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        launcherRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open]);

  return (
    <div className="notification-bell-wrap">
      <button
        ref={launcherRef}
        type="button"
        className="topbar-bell-btn"
        aria-label="الإشعارات"
        title="الإشعارات"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span style={{ fontSize: '16px' }}>🔔</span>
        {unreadCount > 0 && <span className="topbar-bell-badge">{unreadCount}</span>}
      </button>
      {open && (
        <NotificationDropdown
          notifications={notifications}
          loading={loading}
          onMarkRead={markAsRead}
          onMarkAllRead={markAllRead}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
};
