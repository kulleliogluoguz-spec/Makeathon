import { showNotification } from './notifications';

let lastCheckTimestamp = new Date().toISOString();
let pollingInterval = null;
let onNewMessage = null;

export function startPolling(callback) {
  onNewMessage = callback;
  if (pollingInterval) return;

  pollingInterval = setInterval(async () => {
    try {
      const resp = await fetch('/api/v1/dashboard/conversations/');
      if (!resp.ok) return;
      const conversations = await resp.json();

      for (const conv of conversations) {
        if (!conv.last_message_at) continue;

        if (conv.last_message_at > lastCheckTimestamp) {
          try {
            const detailResp = await fetch(`/api/v1/dashboard/conversations/${conv.id}`);
            if (!detailResp.ok) continue;
            const detail = await detailResp.json();
            const msgs = detail.messages || [];
            const lastMsg = msgs[msgs.length - 1];

            if (lastMsg && lastMsg.role === 'user') {
              const channelEmoji = conv.channel === 'instagram' ? '📷' : conv.channel === 'messenger' ? '💬' : '💻';
              showNotification(
                `${channelEmoji} New message`,
                lastMsg.content || 'New message received',
                () => { if (onNewMessage) onNewMessage(conv.id); }
              );
            }
          } catch (e) {}
        }
      }

      lastCheckTimestamp = new Date().toISOString();
    } catch (e) {}
  }, 10000);
}

export function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}
