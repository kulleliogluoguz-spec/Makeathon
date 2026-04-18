let notificationPermission = 'default';
let unreadCount = 0;
let originalTitle = typeof document !== 'undefined' ? document.title : 'Clerque';
let flashInterval = null;

export function initNotifications() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(p => { notificationPermission = p; });
  } else if ('Notification' in window) {
    notificationPermission = Notification.permission;
  }
}

export function playDing() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.frequency.value = 800;
    gain.gain.value = 0.3;
    oscillator.start();
    setTimeout(() => { oscillator.stop(); ctx.close(); }, 200);
  } catch(e) { console.error('Ding error:', e); }
}

export function showNotification(title, body, onClick) {
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
  playDing();
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
    document.title = `(${unreadCount}) New Message — Clerque`;
  } else {
    document.title = originalTitle;
  }
}

function startFlashing() {
  if (flashInterval) return;
  let visible = true;
  flashInterval = setInterval(() => {
    if (visible) {
      document.title = 'New Message!';
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
