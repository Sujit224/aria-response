// Firebase Cloud Messaging service worker
// Required for background push notifications on the Guest PWA
// Place in /public so Vite copies it to the build root

importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js')

// This config is public — it identifies your Firebase project only.
// The actual security is enforced by Firebase Security Rules, not by hiding this key.
firebase.initializeApp({
  apiKey:            self.__FIREBASE_API_KEY__            || '',
  authDomain:        self.__FIREBASE_AUTH_DOMAIN__        || '',
  projectId:         self.__FIREBASE_PROJECT_ID__         || '',
  storageBucket:     self.__FIREBASE_STORAGE_BUCKET__     || '',
  messagingSenderId: self.__FIREBASE_MESSAGING_SENDER_ID__|| '',
  appId:             self.__FIREBASE_APP_ID__             || '',
})

const messaging = firebase.messaging()

// Handle background push notifications
messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification || {}
  const data = payload.data || {}

  self.registration.showNotification(title || '🚨 ARIA Emergency', {
    body:    body || 'Tap to view evacuation instructions',
    icon:    '/icon-192.png',
    badge:   '/icon-192.png',
    vibrate: [200, 100, 200, 100, 300],
    tag:     `aria-incident-${data.incident_id || 'default'}`,
    renotify: true,
    data: { url: `/?venue=${data.venue_id || ''}&room=${data.room_id || ''}` },
    actions: [
      { action: 'view', title: '📍 View Route' },
      { action: 'ack',  title: '✓ Acknowledged' },
    ],
  })
})

// Open the app when notification is clicked
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  if (event.action === 'view' || !event.action) {
    const url = event.notification.data?.url || '/'
    event.waitUntil(clients.openWindow(url))
  }
})
