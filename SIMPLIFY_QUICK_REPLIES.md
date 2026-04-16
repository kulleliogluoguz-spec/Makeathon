Simplify the Quick Reply Templates in Settings. Remove category, keywords fields. Make it just simple question → answer pairs.

Do NOT rewrite files. Do NOT push to git.

## CHANGE 1 — Simplify the Settings UI

In frontend/src/pages/SettingsPage.jsx, find the Quick Reply Templates section. Replace the form and list with a simpler version:

The current form has: title, content, category, keywords. Change it to just:

- **Question** (input) — "What is your return policy?" / "Kargo ne kadar?" / "Do you ship internationally?"
- **Answer** (textarea) — The exact answer the AI should give

The list should show:
```
Q: What is your return policy?
A: You can return any product within 14 days...

Q: Kargo ne kadar?
A: Türkiye içi kargo 2-3 iş günü...
```

Replace the Quick Replies section JSX with this:

```jsx
{/* Quick Replies — Simple Q&A */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
    <div>
      <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Quick Replies</h2>
      <p style={{ fontSize: '0.8rem', color: '#6b7280' }}>If a customer asks this question → AI gives this answer.</p>
    </div>
    <button
      onClick={() => { setQrForm({ title: '', content: '' }); setEditingQR(null); setShowQRForm(true); }}
      style={{ padding: '6px 14px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}
    >+ Add</button>
  </div>

  {quickReplies.length === 0 ? (
    <div style={{ color: '#9ca3af', fontSize: '0.875rem', padding: '1.5rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.5rem' }}>
      No quick replies yet. Example: "What is your return policy?" → "You can return within 14 days..."
    </div>
  ) : (
    quickReplies.map((qr) => (
      <div key={qr.id} style={{ padding: '0.75rem 1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', marginBottom: '0.5rem', background: '#fff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.85rem', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, color: '#3b82f6' }}>Q:</span> {qr.title}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#374151' }}>
              <span style={{ fontWeight: 600, color: '#10b981' }}>A:</span> {qr.content.slice(0, 150)}{qr.content.length > 150 ? '...' : ''}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '4px', marginLeft: '0.75rem', flexShrink: 0 }}>
            <button onClick={() => { setQrForm({ title: qr.title, content: qr.content }); setEditingQR(qr.id); setShowQRForm(true); }}
              style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Edit</button>
            <button onClick={async () => { if (confirm('Delete?')) { await fetch(`/api/v1/quick-replies/${qr.id}`, { method: 'DELETE' }); loadQR(); } }}
              style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
          </div>
        </div>
      </div>
    ))
  )}

  {showQRForm && (
    <div style={{ marginTop: '0.75rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', background: '#f9fafb' }}>
      <div style={{ marginBottom: '0.5rem' }}>
        <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>If the customer asks:</label>
        <input type="text" placeholder='e.g. "What is your return policy?"' value={qrForm.title} onChange={(e) => setQrForm({ ...qrForm, title: e.target.value })}
          style={{ width: '100%', padding: '8px 12px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', boxSizing: 'border-box' }} />
      </div>
      <div style={{ marginBottom: '0.75rem' }}>
        <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Answer with:</label>
        <textarea placeholder="The exact answer the AI should give..." value={qrForm.content} onChange={(e) => setQrForm({ ...qrForm, content: e.target.value })} rows={3}
          style={{ width: '100%', padding: '8px 12px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
      </div>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button onClick={async () => {
          const method = editingQR ? 'PATCH' : 'POST';
          const url = editingQR ? `/api/v1/quick-replies/${editingQR}` : '/api/v1/quick-replies/';
          await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: qrForm.title, content: qrForm.content, category: '', keywords: qrForm.title }) });
          setShowQRForm(false); setEditingQR(null); loadQR();
        }} disabled={!qrForm.title || !qrForm.content}
          style={{ padding: '6px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer', opacity: (!qrForm.title || !qrForm.content) ? 0.4 : 1 }}>
          {editingQR ? 'Save' : 'Add'}</button>
        <button onClick={() => { setShowQRForm(false); setEditingQR(null); }}
          style={{ padding: '6px 16px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
      </div>
    </div>
  )}
</section>
```

Note: The backend still stores category and keywords fields — we just auto-set keywords to the question text when saving. This way the AI matching still works.

## CHANGE 2 — Update the LLM prompt for quick replies

In instagram.py, messenger.py, and livechat.py — find where quick_replies_text is built. Change the format to be clearer Q&A:

Replace the quick replies prompt section with:

```python
quick_replies_text = ""
try:
    from app.models.quick_reply import QuickReply
    async with async_session() as session:
        qr_result = await session.execute(select(QuickReply))
        qr_list = qr_result.scalars().all()
        if qr_list:
            quick_replies_text = "\n\n## PREDEFINED Q&A\nWhen the customer asks about any of these topics, use the provided answer. Do NOT make up a different answer — use the exact text provided:\n\n"
            for qr in qr_list:
                quick_replies_text += f"QUESTION: {qr.title}\nANSWER: {qr.content}\n\n"
except Exception as e:
    print(f"Quick replies load error: {e}")
```

Do this in all 3 files.

## CHANGE 3 — Update i18n

In frontend/src/lib/i18n.js, update the quick reply keys:

English:
```javascript
qr_title: "Quick Replies",
qr_subtitle: "If a customer asks this question → AI gives this answer.",
qr_add: "+ Add",
qr_no_templates: 'No quick replies yet. Example: "What is your return policy?" → "You can return within 14 days..."',
qr_question_label: "If the customer asks:",
qr_answer_label: "Answer with:",
qr_question_placeholder: 'e.g. "What is your return policy?"',
qr_answer_placeholder: "The exact answer the AI should give...",
```

Turkish:
```javascript
qr_title: "Hazır Cevaplar",
qr_subtitle: "Müşteri bu soruyu sorarsa → AI bu cevabı verir.",
qr_add: "+ Ekle",
qr_no_templates: 'Henüz hazır cevap yok. Örnek: "İade politikanız nedir?" → "14 gün içinde iade yapabilirsiniz..."',
qr_question_label: "Müşteri sorarsa:",
qr_answer_label: "Cevap:",
qr_question_placeholder: 'ör. "İade politikanız nedir?"',
qr_answer_placeholder: "AI'ın vereceği cevap...",
```

Do NOT change anything else. Do NOT push to git.
