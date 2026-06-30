/* global importScripts, firebase, self, clients */

importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

const params = new URL(self.location.href).searchParams;
const config = {
  apiKey: params.get('apiKey'),
  authDomain: params.get('authDomain'),
  projectId: params.get('projectId'),
  messagingSenderId: params.get('messagingSenderId'),
  appId: params.get('appId'),
};

try {
  if (config.apiKey && config.projectId && firebase?.apps?.length === 0) {
    firebase.initializeApp(config);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage((payload) => {
      const title = payload.notification?.title || payload.data?.title || 'EduMind';
      const options = {
        body: payload.notification?.body || payload.data?.body || 'لديك إشعار جديد.',
        data: payload.data || {},
        icon: '/favicon.svg',
        badge: '/favicon.svg',
      };
      self.registration.showNotification(title, options);
    });
  }
} catch (error) {
  console.warn('Firebase messaging service worker not configured', error);
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.action_url || '/notifications';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      const existing = clientList.find((client) => 'focus' in client);
      if (existing) {
        existing.focus();
        existing.navigate(url);
        return;
      }
      return clients.openWindow(url);
    }),
  );
});
