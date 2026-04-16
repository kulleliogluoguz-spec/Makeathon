Move the Live Chat embed code section into the existing Settings page. Remove the standalone LiveChatSetupPage.

RULES: Do NOT rewrite files. Do NOT push to git.

1. In frontend/src/App.jsx:
   - DELETE the LiveChatSetupPage import line
   - DELETE the /livechat Route
   - DELETE the "Live Chat" nav link

2. In frontend/src/pages/SettingsPage.jsx, add a new section at the bottom (before the Save button) for the embed code:

Add state at top of component:
```jsx
const [personas, setPersonas] = useState([]);
const [selectedPersona, setSelectedPersona] = useState('');
const [copied, setCopied] = useState(false);

useEffect(() => {
  fetch('/api/v1/personas/').then(r => r.json()).then(setPersonas).catch(() => {});
}, []);
```

Add this section BEFORE the Save button:

```jsx
{/* Live Chat Widget */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
  <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>Live Chat Widget</h2>
  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
    Add this code to any website to enable AI chat. Paste before the closing &lt;/body&gt; tag.
  </p>

  <div style={{ marginBottom: '1rem' }}>
    <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>PERSONA</label>
    <select
      value={selectedPersona}
      onChange={(e) => setSelectedPersona(e.target.value)}
      style={{ width: '100%', padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }}
    >
      <option value="">Select persona...</option>
      {personas.map(p => (
        <option key={p.id} value={p.id}>{p.name}</option>
      ))}
    </select>
  </div>

  {selectedPersona && (
    <>
      <div style={{
        background: '#111', color: '#10b981', padding: '1rem',
        borderRadius: '0.5rem', fontFamily: 'monospace', fontSize: '0.75rem',
        overflowX: 'auto', marginBottom: '0.75rem', lineHeight: 1.5,
      }}>
        {`<script src="${window.location.origin}/widget/chat.js" data-persona-id="${selectedPersona}"></script>`}
      </div>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button
          onClick={() => {
            navigator.clipboard.writeText(`<script src="${window.location.origin}/widget/chat.js" data-persona-id="${selectedPersona}"></script>`);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }}
          style={{
            padding: '6px 16px', background: '#000', color: '#fff',
            border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
          }}
        >{copied ? '✓ Copied!' : 'Copy Code'}</button>
        <button
          onClick={() => {
            var s = document.createElement('script');
            s.src = '/widget/chat.js';
            s.setAttribute('data-persona-id', selectedPersona);
            document.body.appendChild(s);
          }}
          style={{
            padding: '6px 16px', background: '#fff', color: '#000',
            border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
          }}
        >Test on This Page</button>
      </div>
    </>
  )}
</section>
```

3. You can delete frontend/src/pages/LiveChatSetupPage.jsx or leave it — it's no longer referenced.

That is ALL. Do NOT change any other file. Do NOT push to git.
