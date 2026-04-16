Browser notifications and test sound button are not working. Debug and fix:

1. Check if notifications.js is properly imported in App.jsx and SettingsPage.jsx

2. The test sound button in SettingsPage might be using invalid base64 audio. Replace with Web Audio API.

In SettingsPage.jsx, find the test sound button onClick. Replace it with:

```jsx
onClick={() => {
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
  } catch(e) { console.error('Sound error:', e); }
}}
```

3. In frontend/src/lib/notifications.js, replace the entire playDing function with:

```javascript
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
```

Also remove the DING_SOUND base64 constant and audioElement variable from notifications.js since they are no longer needed.

4. Make sure initNotifications() is called in App.jsx useEffect on mount. Check that the import exists and the function is called.

5. For the Enable Browser Notifications button in SettingsPage, make sure it works:

```jsx
onClick={async () => {
  if ('Notification' in window) {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      new Notification('Notifications enabled!', { body: 'You will now receive alerts for new messages.' });
    } else {
      alert('Notifications were blocked. Please enable them in your browser settings.');
    }
  } else {
    alert('Your browser does not support notifications.');
  }
}}
```

6. Make sure messagePoller.js is imported and startPolling() is called in App.jsx useEffect.

Do NOT rewrite files completely. Only fix the specific functions and buttons mentioned. Do NOT push to git.
