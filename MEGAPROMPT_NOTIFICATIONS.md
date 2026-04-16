# PROMPT: Browser Notifications + Sound Alerts

## CRITICAL RULES
- Do NOT rewrite any existing file
- Do NOT push to git
- Do NOT touch backend — this is 100% frontend-only

## WHAT THIS DOES

When a new message arrives on any channel (Instagram, Messenger, LiveChat):
1. Browser push notification pops up (with customer name + message preview)
2. Sound alert plays (subtle ding)
3. Unread message badge on navbar "Conversations" link
4. Tab title flashes: "(3) New Messages — Persona Builder"

Works even when user is on a different tab.

## IMPLEMENTATION

### New file: `frontend/src/lib/notifications.js`

```javascript
let notificationPermission = 'default';
let unreadCount = 0;
let originalTitle = document.title;
let flashInterval = null;

// Audio — tiny base64 encoded ding sound (no external file needed)
const DING_SOUND = 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAABYYzAAAAAAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAABYYzAAAAAAAAAAAAAAAAAAAA';

let audioElement = null;

export function initNotifications() {
  // Request permission
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(p => { notificationPermission = p; });
  } else if ('Notification' in window) {
    notificationPermission = Notification.permission;
  }

  // Pre-load audio
  audioElement = new Audio(DING_SOUND);
  audioElement.volume = 0.5;
}

export function playDing() {
  try {
    if (audioElement) {
      audioElement.currentTime = 0;
      audioElement.play().catch(() => {});
    }
  } catch (e) {}
}

export function showNotification(title, body, onClick) {
  // Browser notification
  if ('Notification' in window && Notification.permission === 'granted') {
    const n = new Notification(title, {
      body: body.slice(0, 100),
      icon: '/favicon.ico',
      tag: 'new-message',
      renotify: true,
    });
    if (onClick) {
      n.onclick = () => { window.focus(); onClick(); n.close(); };
    }
    setTimeout(() => n.close(), 5000);
  }

  // Sound
  playDing();

  // Tab title flash
  incrementUnread();
}

export function incrementUnread() {
  unreadCount++;
  updateTabTitle();
  startFlashing();
}

export function resetUnread() {
  unreadCount = 0;
  updateTabTitle();
  stopFlashing();
}

function updateTabTitle() {
  if (unreadCount > 0) {
    document.title = `(${unreadCount}) New Message — Persona Builder`;
  } else {
    document.title = originalTitle;
  }
}

function startFlashing() {
  if (flashInterval) return;
  let visible = true;
  flashInterval = setInterval(() => {
    if (visible) {
      document.title = `💬 New Message!`;
    } else {
      updateTabTitle();
    }
    visible = !visible;
  }, 1000);
}

function stopFlashing() {
  if (flashInterval) {
    clearInterval(flashInterval);
    flashInterval = null;
  }
  document.title = originalTitle;
}

export function getUnreadCount() {
  return unreadCount;
}

// Listen for page visibility — reset unread when user comes back to tab
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && unreadCount > 0) {
    // Don't auto-reset — let the user explicitly view conversations to reset
  }
});
```

### New file: `frontend/src/lib/messagePoller.js`

```javascript
/**
 * Polls for new messages every 10 seconds.
 * Compares latest message timestamp to detect new messages.
 * Triggers notifications when new messages arrive.
 */

import { showNotification, getUnreadCount } from './notifications';

let lastCheckTimestamp = new Date().toISOString();
let pollingInterval = null;
let onNewMessage = null; // callback

export function startPolling(callback) {
  onNewMessage = callback;
  if (pollingInterval) return;

  pollingInterval = setInterval(async () => {
    try {
      const resp = await fetch('/api/v1/conversations/');
      if (!resp.ok) return;
      const conversations = await resp.json();

      for (const conv of conversations) {
        if (!conv.last_message_at) continue;

        // Check if this conversation has a new message since last check
        if (conv.last_message_at > lastCheckTimestamp) {
          // Get the latest message
          try {
            const detailResp = await fetch(`/api/v1/conversations/${conv.id}`);
            if (!detailResp.ok) continue;
            const detail = await detailResp.json();
            const msgs = detail.messages || [];
            const lastMsg = msgs[msgs.length - 1];

            if (lastMsg && lastMsg.role === 'user') {
              // New customer message — notify
              const channelEmoji = conv.channel === 'instagram' ? '📷' : conv.channel === 'messenger' ? '💬' : '💻';
              showNotification(
                `${channelEmoji} New message`,
                lastMsg.content || 'New message received',
                () => {
                  if (onNewMessage) onNewMessage(conv.id);
                }
              );
            }
          } catch (e) {}
        }
      }

      lastCheckTimestamp = new Date().toISOString();
    } catch (e) {}
  }, 10000); // every 10 seconds
}

export function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}
```

### Edit: `frontend/src/App.jsx`

Add notification initialization and polling. At the top, add imports:

```jsx
import { initNotifications, getUnreadCount, resetUnread } from './lib/notifications';
import { startPolling } from './lib/messagePoller';
import { useEffect, useState } from 'react';
```

Inside the App component (or at the top level), add:

```jsx
const [unread, setUnread] = useState(0);

useEffect(() => {
  initNotifications();
  startPolling((convId) => {
    setUnread(getUnreadCount());
    // Optionally navigate to conversation
  });

  // Update unread count every second
  const interval = setInterval(() => {
    setUnread(getUnreadCount());
  }, 1000);

  return () => clearInterval(interval);
}, []);
```

In the navbar, find the "Conversations" link. Add an unread badge next to it:

```jsx
<Link to="/conversations" onClick={() => resetUnread()}>
  {t('nav_conversations')}
  {unread > 0 && (
    <span style={{
      marginLeft: '6px',
      background: '#ef4444',
      color: '#fff',
      fontSize: '0.65rem',
      fontWeight: 700,
      padding: '2px 6px',
      borderRadius: '9999px',
      minWidth: '18px',
      textAlign: 'center',
      display: 'inline-block',
    }}>{unread}</span>
  )}
</Link>
```

Also import resetUnread:
```jsx
import { initNotifications, getUnreadCount, resetUnread } from './lib/notifications';
```

When user clicks "Conversations" link, reset unread count.

### Edit: `frontend/src/pages/ConversationsPage.jsx`

When the page mounts, reset unread:

```jsx
import { resetUnread } from '../lib/notifications';

// Inside the component, in useEffect on mount:
useEffect(() => {
  resetUnread();
}, []);
```

### Edit: `frontend/src/pages/SettingsPage.jsx`

Add a notification settings section. Insert BEFORE the Language section:

```jsx
{/* Notifications */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
  <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>Notifications</h2>
  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
    Get notified when new messages arrive.
  </p>
  <div style={{ display: 'flex', gap: '0.75rem' }}>
    <button
      onClick={() => {
        if ('Notification' in window) {
          Notification.requestPermission().then(p => {
            alert(p === 'granted' ? 'Notifications enabled!' : 'Notifications blocked. Enable in browser settings.');
          });
        }
      }}
      style={{
        padding: '8px 16px', background: '#000', color: '#fff',
        border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
      }}
    >
      {typeof Notification !== 'undefined' && Notification.permission === 'granted' ? '✓ Notifications Enabled' : 'Enable Browser Notifications'}
    </button>
    <button
      onClick={() => {
        const audio = new Audio('data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAABYYzAAAAAAAAAAAAAAAAAAAA');
        audio.volume = 0.5;
        audio.play();
      }}
      style={{
        padding: '8px 16px', background: '#fff', color: '#374151',
        border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
      }}
    >🔊 Test Sound</button>
  </div>
</section>
```

### Edit: `frontend/src/lib/i18n.js`

Add keys:

English:
```javascript
notif_title: "Notifications",
notif_desc: "Get notified when new messages arrive.",
notif_enable: "Enable Browser Notifications",
notif_enabled: "Notifications Enabled",
notif_test_sound: "Test Sound",
```

Turkish:
```javascript
notif_title: "Bildirimler",
notif_desc: "Yeni mesaj geldiğinde bildirim alın.",
notif_enable: "Tarayıcı Bildirimlerini Aç",
notif_enabled: "Bildirimler Açık",
notif_test_sound: "Ses Testi",
```

## HOW IT WORKS

1. User opens platform → `initNotifications()` requests browser permission
2. `startPolling()` checks /api/v1/conversations/ every 10 seconds
3. If a conversation has a newer `last_message_at` than last check → new message detected
4. If the new message is from "user" (customer) → triggers:
   - Browser push notification with channel emoji + message preview
   - Ding sound alert
   - Unread badge (red circle with count) on "Conversations" nav link
   - Tab title flashes: "(3) New Message — Persona Builder"
5. User clicks "Conversations" → unread count resets
6. User clicks the browser notification → window focuses

## TEST PLAN

1. Apply changes. Restart frontend.
2. Open Settings → click "Enable Browser Notifications" → allow in browser popup.
3. Click "Test Sound" → hear a ding.
4. Open platform in one tab. From another device, send an Instagram DM.
5. Within 10 seconds: browser notification pops up + ding sound + red badge appears on Conversations + tab title flashes.
6. Click Conversations → badge disappears, title resets.

## SUMMARY

NEW:
- frontend/src/lib/notifications.js
- frontend/src/lib/messagePoller.js

EDITED:
- frontend/src/App.jsx (imports + init + unread badge on nav)
- frontend/src/pages/ConversationsPage.jsx (reset unread on mount)
- frontend/src/pages/SettingsPage.jsx (notification settings section)
- frontend/src/lib/i18n.js (new keys)

## DO NOT
- ❌ DO NOT touch backend
- ❌ DO NOT rewrite any file
- ❌ DO NOT push to git

## START NOW
