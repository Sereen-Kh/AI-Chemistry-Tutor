import { useCallback, useMemo, useState } from 'react';
import { notificationsApi } from '../api/notificationsApi';

type PushStatus = 'unsupported' | 'default' | 'granted' | 'denied' | 'configured' | 'error';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string | undefined,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID as string | undefined,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string | undefined,
};

const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY as string | undefined;

const isFirebaseConfigPresent = () => (
  Boolean(firebaseConfig.apiKey)
  && Boolean(firebaseConfig.projectId)
  && Boolean(firebaseConfig.messagingSenderId)
  && Boolean(firebaseConfig.appId)
  && Boolean(vapidKey)
);

const importRuntime = async (specifier: string): Promise<any> => {
  const loader = new Function('specifier', 'return import(specifier)');
  return loader(specifier);
};

export const usePushNotifications = () => {
  const initialPermission = typeof window !== 'undefined' && 'Notification' in window
    ? Notification.permission
    : 'denied';
  const [permission, setPermission] = useState<NotificationPermission>(initialPermission);
  const [status, setStatus] = useState<PushStatus>(
    typeof window === 'undefined' || !('serviceWorker' in navigator) || !('Notification' in window)
      ? 'unsupported'
      : initialPermission,
  );
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const canRequest = useMemo(() => status !== 'unsupported' && permission !== 'denied', [permission, status]);

  const enablePush = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        setStatus('unsupported');
        setError('المتصفح لا يدعم إشعارات الويب.');
        return;
      }

      const nextPermission = await Notification.requestPermission();
      setPermission(nextPermission);
      if (nextPermission !== 'granted') {
        setStatus(nextPermission);
        setError('لم يتم منح صلاحية الإشعارات.');
        return;
      }

      if (!isFirebaseConfigPresent()) {
        setStatus('granted');
        setError('تم منح الصلاحية، لكن إعدادات Firebase غير مكتملة في الواجهة.');
        return;
      }

      const swParams = new URLSearchParams({
        apiKey: firebaseConfig.apiKey ?? '',
        authDomain: firebaseConfig.authDomain ?? '',
        projectId: firebaseConfig.projectId ?? '',
        messagingSenderId: firebaseConfig.messagingSenderId ?? '',
        appId: firebaseConfig.appId ?? '',
      });
      const registration = await navigator.serviceWorker.register(`/firebase-messaging-sw.js?${swParams.toString()}`);
      const appModule = await importRuntime('firebase/app');
      const messagingModule = await importRuntime('firebase/messaging');
      const app = appModule.initializeApp(firebaseConfig);
      const messaging = messagingModule.getMessaging(app);
      const token = await messagingModule.getToken(messaging, {
        vapidKey,
        serviceWorkerRegistration: registration,
      });

      if (!token) {
        setStatus('error');
        setError('تعذر إنشاء رمز FCM للمتصفح.');
        return;
      }

      await notificationsApi.registerPushToken({
        token,
        platform: 'web',
        device_name: navigator.platform || 'Web browser',
        browser: navigator.userAgent.slice(0, 80),
      });
      setStatus('configured');
      window.dispatchEvent(new Event('notifications-updated'));
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'تعذر تفعيل إشعارات الويب.');
    } finally {
      setBusy(false);
    }
  }, []);

  return {
    permission,
    status,
    busy,
    error,
    canRequest,
    enablePush,
  };
};
