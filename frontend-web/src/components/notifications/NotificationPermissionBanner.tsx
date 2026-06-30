import { Button } from '../DesignSystem';
import { usePushNotifications } from '../../hooks/usePushNotifications';

export const NotificationPermissionBanner = () => {
  const { permission, status, busy, error, canRequest, enablePush } = usePushNotifications();

  if (status === 'unsupported' || permission === 'granted' && status === 'configured') return null;

  return (
    <section className="notification-permission-banner" aria-label="تفعيل إشعارات EduMind">
      <div>
        <strong>فعّل الإشعارات لتصلك تذكيرات الدروس والمراجعة</strong>
        <span>
          لن نطلب الصلاحية تلقائياً. اضغط الزر عندما تريد استقبال تذكيرات المتصفح.
        </span>
        {error && <em>{error}</em>}
      </div>
      <Button onClick={() => void enablePush()} disabled={!canRequest || busy}>
        {busy ? 'جاري التفعيل...' : 'تفعيل الإشعارات'}
      </Button>
    </section>
  );
};
