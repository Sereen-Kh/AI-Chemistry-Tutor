import { useEffect, useState } from 'react';
import { notificationsApi } from '../api';
import type { NotificationPreferenceItem } from '../api/notificationsApi';
import { Button, ErrorBanner, LoadingSkeleton, PageHeader } from '../components/DesignSystem';
import { NotificationPermissionBanner } from '../components/notifications/NotificationPermissionBanner';

const defaultPreferences: NotificationPreferenceItem = {
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
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
};

const ToggleRow = ({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) => (
  <label className="notification-setting-row">
    <span>
      <strong>{label}</strong>
      <small>{description}</small>
    </span>
    <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
  </label>
);

export const NotificationSettingsPage = () => {
  const [preferences, setPreferences] = useState<NotificationPreferenceItem>(defaultPreferences);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const loaded = await notificationsApi.getPreferences();
      setPreferences({ ...defaultPreferences, ...loaded });
    } catch {
      setError('تعذر تحميل إعدادات الإشعارات.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const update = async (updates: Partial<NotificationPreferenceItem>) => {
    setSaving(true);
    setError('');
    setStatus('');
    const next = { ...preferences, ...updates };
    if ('daily_study_reminder_time' in updates) next.reminder_time_local = updates.daily_study_reminder_time || next.reminder_time_local;
    if ('exam_reminder_enabled' in updates) next.exam_reminders_enabled = Boolean(updates.exam_reminder_enabled);
    if ('daily_study_reminder_enabled' in updates) next.lesson_reminders_enabled = Boolean(updates.daily_study_reminder_enabled);
    setPreferences(next);
    try {
      const saved = await notificationsApi.updatePreferences(updates);
      setPreferences({ ...next, ...saved });
      setStatus('تم حفظ الإعدادات.');
      window.dispatchEvent(new Event('notifications-updated'));
    } catch {
      setError('تعذر حفظ إعدادات الإشعارات.');
    } finally {
      setSaving(false);
    }
  };

  const sendTest = async () => {
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await notificationsApi.sendTestNotification();
      setStatus('تم إرسال إشعار اختبار.');
      window.dispatchEvent(new Event('notifications-updated'));
    } catch {
      setError('تعذر إرسال إشعار الاختبار.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-stack notification-settings-page" dir="rtl">
      <PageHeader
        eyebrow="تفضيلات التذكير"
        title="إعدادات الإشعارات"
        subtitle="تحكم بتذكيرات الدراسة والاختبارات والبطاقات بدون إزعاج."
        action={<Button onClick={() => void sendTest()} disabled={saving}>إرسال اختبار</Button>}
      />

      <NotificationPermissionBanner />
      {error && <ErrorBanner message={error} onRetry={load} />}
      {status && <div className="success-banner">{status}</div>}

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : (
        <section className="notification-settings-card">
          <ToggleRow
            label="تفعيل الإشعارات"
            description="المفتاح الرئيسي لتذكيرات EduMind."
            checked={preferences.in_app_enabled}
            onChange={(checked) => void update({ in_app_enabled: checked })}
          />
          <ToggleRow
            label="داخل التطبيق"
            description="عرض الإشعارات داخل مركز الإشعارات."
            checked={preferences.in_app_enabled}
            onChange={(checked) => void update({ in_app_enabled: checked })}
          />
          <ToggleRow
            label="Push"
            description="إرسال تنبيهات قصيرة إلى المتصفح أو الهاتف."
            checked={preferences.push_enabled}
            onChange={(checked) => void update({ push_enabled: checked })}
          />
          <ToggleRow
            label="تذكير درس اليوم"
            description="تنبيه يومي عندما توجد مهمة دراسة مجدولة."
            checked={preferences.daily_study_reminder_enabled}
            onChange={(checked) => void update({ daily_study_reminder_enabled: checked })}
          />
          <label className="notification-setting-row">
            <span>
              <strong>وقت تذكير الدراسة</strong>
              <small>سيتم احترام المنطقة الزمنية وساعات الهدوء.</small>
            </span>
            <input
              type="time"
              value={preferences.daily_study_reminder_time}
              onChange={(event) => void update({ daily_study_reminder_time: event.target.value })}
            />
          </label>
          <ToggleRow
            label="تذكير الاختبارات"
            description="7 أيام، 3 أيام، ويوم واحد قبل الاختبار."
            checked={preferences.exam_reminder_enabled}
            onChange={(checked) => void update({ exam_reminder_enabled: checked })}
          />
          <ToggleRow
            label="البطاقات المستحقة"
            description="تنبيه عند وجود بطاقات مراجعة جاهزة."
            checked={preferences.flashcards_reminder_enabled}
            onChange={(checked) => void update({ flashcards_reminder_enabled: checked })}
          />
          <ToggleRow
            label="الدروس المتأخرة"
            description="تذكير يومي للدروس المجدولة التي لم تكتمل."
            checked={preferences.overdue_lesson_reminder_enabled}
            onChange={(checked) => void update({ overdue_lesson_reminder_enabled: checked })}
          />
          <ToggleRow
            label="نقاط الضعف"
            description="اقتراح تدريب قصير عند انخفاض نتيجة موضوع."
            checked={preferences.weak_topic_reminder_enabled}
            onChange={(checked) => void update({ weak_topic_reminder_enabled: checked })}
          />
          <ToggleRow
            label="ساعات الهدوء"
            description="لا ترسل Push أثناء هذه الفترة."
            checked={preferences.quiet_hours_enabled}
            onChange={(checked) => void update({ quiet_hours_enabled: checked })}
          />
          <div className="notification-settings-times">
            <label>
              بداية الهدوء
              <input
                type="time"
                value={preferences.quiet_hours_start}
                onChange={(event) => void update({ quiet_hours_start: event.target.value })}
              />
            </label>
            <label>
              نهاية الهدوء
              <input
                type="time"
                value={preferences.quiet_hours_end}
                onChange={(event) => void update({ quiet_hours_end: event.target.value })}
              />
            </label>
            <label>
              المنطقة الزمنية
              <input
                value={preferences.timezone}
                onChange={(event) => setPreferences((current) => ({ ...current, timezone: event.target.value }))}
                onBlur={(event) => void update({ timezone: event.target.value })}
              />
            </label>
          </div>
        </section>
      )}
    </div>
  );
};
