# PROMPT: Quick Reply Templates

## CRITICAL RULES
- ADDITIVE only. Do NOT rewrite files.
- FIRST run: `git add -A && git commit -m "checkpoint before quick replies"`
- Do NOT push to git.
- Do NOT touch persona builder, voice builder, catalog, or channel webhooks.

## WHAT THIS DOES

Admin creates quick reply templates (e.g. "Return Policy", "Working Hours", "Shipping Info"). These are pre-written answers to common questions. Two uses:

1. **AI uses them automatically** — when a customer asks a question that matches a template, AI uses the template text instead of making something up. This ensures consistent, accurate answers.
2. **Manual use** — in the Conversations detail panel, a "Quick Replies" button shows the template list. Click one to send it directly.

## BACKEND

### New file: `backend/app/models/quick_reply.py`

```python
"""Quick reply templates for common questions."""

from sqlalchemy import Column, String, Text, DateTime, Integer
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class QuickReply(Base):
    __tablename__ = "quick_replies"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)  # Short label: "Return Policy"
    content = Column(Text, nullable=False)   # Full reply text
    category = Column(String, default="")    # Optional grouping: "shipping", "payment", etc.
    keywords = Column(String, default="")    # Comma-separated trigger words: "return,refund,exchange"
    use_count = Column(Integer, default=0)   # How many times used
    persona_id = Column(String, default="")  # Optional: link to specific persona, empty = all
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.quick_reply import QuickReply  # noqa
```

### New file: `backend/app/api/quick_replies.py`

```python
"""Quick reply templates CRUD API."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.quick_reply import QuickReply

router = APIRouter()


@router.get("/quick-replies/")
async def list_quick_replies(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(QuickReply).order_by(desc(QuickReply.use_count))
    result = await db.execute(query)
    replies = result.scalars().all()

    if category:
        replies = [r for r in replies if r.category == category]
    if search:
        s = search.lower()
        replies = [r for r in replies if s in r.title.lower() or s in r.content.lower() or s in (r.keywords or "").lower()]

    return [_serialize(r) for r in replies]


@router.post("/quick-replies/")
async def create_quick_reply(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("title") or not body.get("content"):
        raise HTTPException(status_code=400, detail="Title and content are required")

    reply = QuickReply(
        title=body["title"],
        content=body["content"],
        category=body.get("category", ""),
        keywords=body.get("keywords", ""),
        persona_id=body.get("persona_id", ""),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return _serialize(reply)


@router.patch("/quick-replies/{reply_id}")
async def update_quick_reply(reply_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuickReply).where(QuickReply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404)

    for field in ("title", "content", "category", "keywords", "persona_id"):
        if field in body:
            setattr(reply, field, body[field])
    reply.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(reply)
    return _serialize(reply)


@router.delete("/quick-replies/{reply_id}")
async def delete_quick_reply(reply_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuickReply).where(QuickReply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404)
    await db.delete(reply)
    await db.commit()
    return {"status": "deleted"}


@router.post("/quick-replies/{reply_id}/use")
async def increment_use_count(reply_id: str, db: AsyncSession = Depends(get_db)):
    """Increment use count when a template is used."""
    result = await db.execute(select(QuickReply).where(QuickReply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404)
    reply.use_count = (reply.use_count or 0) + 1
    await db.commit()
    return {"status": "ok", "use_count": reply.use_count}


@router.get("/quick-replies/match")
async def match_quick_reply(q: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Find the best matching quick reply for a customer message."""
    result = await db.execute(select(QuickReply))
    replies = result.scalars().all()

    q_lower = q.lower()
    matches = []
    for r in replies:
        score = 0
        keywords = [k.strip().lower() for k in (r.keywords or "").split(",") if k.strip()]
        for kw in keywords:
            if kw in q_lower:
                score += 10
        if r.title.lower() in q_lower:
            score += 5
        if score > 0:
            matches.append({"reply": _serialize(r), "score": score})

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {"matches": matches[:3]}


def _serialize(r: QuickReply) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "content": r.content,
        "category": r.category or "",
        "keywords": r.keywords or "",
        "use_count": r.use_count or 0,
        "persona_id": r.persona_id or "",
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.quick_replies import router as quick_replies_router
```

Add include_router:
```python
app.include_router(quick_replies_router, prefix="/api/v1", tags=["Quick Replies"])
```

### Edit: `backend/app/api/instagram.py`

Make AI aware of quick reply templates. In the get_reply function (or wherever the LLM system prompt is built), AFTER loading products and scoring context, add:

```python
# Load quick reply templates for consistent answers
quick_replies_text = ""
try:
    from app.models.quick_reply import QuickReply
    async with async_session() as session:
        qr_result = await session.execute(select(QuickReply))
        qr_list = qr_result.scalars().all()
        if qr_list:
            quick_replies_text = "\n\n## QUICK REPLY TEMPLATES\nUse these pre-approved answers when the customer asks about these topics. Use the exact content, do not make up different information:\n\n"
            for qr in qr_list:
                quick_replies_text += f"Topic: {qr.title}\nKeywords: {qr.keywords}\nAnswer: {qr.content}\n\n"
except Exception as e:
    print(f"Quick replies load error: {e}")

full_system_prompt = system_prompt + products_text + scoring_context + quick_replies_text
```

Do the same in `backend/app/api/messenger.py` — add the same quick_replies_text block before building full_system_prompt.

Do the same in `backend/app/api/livechat.py` — in the generate_livechat_reply function, add quick replies to the prompt.

## FRONTEND

### Edit: `frontend/src/pages/ConversationsPage.jsx`

Add a "Quick Replies" panel in the conversation detail. Add state:
```jsx
const [quickReplies, setQuickReplies] = useState([]);
const [showQuickReplies, setShowQuickReplies] = useState(false);
```

Load quick replies when detail opens (add to openDetail function):
```jsx
fetch('/api/v1/quick-replies/').then(r => r.json()).then(setQuickReplies).catch(() => {});
```

Add a "Quick Replies" button next to the "Export PDF" button in the detail panel:

```jsx
<button
  onClick={() => setShowQuickReplies(!showQuickReplies)}
  style={{
    padding: '3px 10px', fontSize: '0.7rem', background: showQuickReplies ? '#000' : '#fff',
    color: showQuickReplies ? '#fff' : '#374151',
    border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
  }}
>⚡ Quick Replies</button>
```

Below that button bar, show the quick replies list when toggled:

```jsx
{showQuickReplies && quickReplies.length > 0 && (
  <div style={{ marginBottom: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
    {quickReplies.map((qr) => (
      <div
        key={qr.id}
        onClick={async () => {
          // Send this reply to the customer via the appropriate channel
          // For now just copy to clipboard
          navigator.clipboard.writeText(qr.content);
          await fetch(`/api/v1/quick-replies/${qr.id}/use`, { method: 'POST' });
          alert('Copied to clipboard: ' + qr.title);
        }}
        style={{
          padding: '8px', borderBottom: '1px solid #f3f4f6', cursor: 'pointer',
          fontSize: '0.8rem',
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        <div style={{ fontWeight: 600, marginBottom: '2px' }}>⚡ {qr.title}</div>
        <div style={{ color: '#6b7280', fontSize: '0.75rem' }}>{qr.content.slice(0, 100)}{qr.content.length > 100 ? '...' : ''}</div>
      </div>
    ))}
  </div>
)}
```

### Edit: `frontend/src/pages/SettingsPage.jsx`

Add a Quick Replies management section. Add state:
```jsx
const [quickReplies, setQuickReplies] = useState([]);
const [showQRForm, setShowQRForm] = useState(false);
const [qrForm, setQrForm] = useState({ title: '', content: '', category: '', keywords: '' });
const [editingQR, setEditingQR] = useState(null);

const loadQR = async () => {
  fetch('/api/v1/quick-replies/').then(r => r.json()).then(setQuickReplies).catch(() => {});
};
useEffect(() => { loadQR(); }, []);
```

Add this section BEFORE the Live Chat Widget section:

```jsx
{/* Quick Replies */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
    <div>
      <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Quick Reply Templates</h2>
      <p style={{ fontSize: '0.8rem', color: '#6b7280' }}>Pre-written answers for common questions. AI uses these automatically.</p>
    </div>
    <button
      onClick={() => { setQrForm({ title: '', content: '', category: '', keywords: '' }); setEditingQR(null); setShowQRForm(true); }}
      style={{ padding: '6px 14px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}
    >+ Add Template</button>
  </div>

  {quickReplies.length === 0 ? (
    <div style={{ color: '#9ca3af', fontSize: '0.875rem', padding: '1rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.5rem' }}>
      No templates yet. Add common answers like return policy, shipping info, working hours.
    </div>
  ) : (
    quickReplies.map((qr) => (
      <div key={qr.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '0.75rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', marginBottom: '0.5rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>⚡ {qr.title}</div>
          <div style={{ fontSize: '0.8rem', color: '#374151', marginTop: '2px' }}>{qr.content.slice(0, 120)}{qr.content.length > 120 ? '...' : ''}</div>
          <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '4px' }}>
            {qr.category && `${qr.category} · `}Keywords: {qr.keywords || 'none'} · Used {qr.use_count}x
          </div>
        </div>
        <div style={{ display: 'flex', gap: '4px', marginLeft: '0.5rem' }}>
          <button onClick={() => { setQrForm({ title: qr.title, content: qr.content, category: qr.category, keywords: qr.keywords }); setEditingQR(qr.id); setShowQRForm(true); }}
            style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Edit</button>
          <button onClick={async () => { if (confirm('Delete?')) { await fetch(`/api/v1/quick-replies/${qr.id}`, { method: 'DELETE' }); loadQR(); } }}
            style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
        </div>
      </div>
    ))
  )}

  {showQRForm && (
    <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', background: '#f9fafb' }}>
      <div style={{ marginBottom: '0.5rem' }}>
        <input type="text" placeholder="Title (e.g. Return Policy)" value={qrForm.title} onChange={(e) => setQrForm({ ...qrForm, title: e.target.value })}
          style={{ width: '100%', padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }} />
      </div>
      <div style={{ marginBottom: '0.5rem' }}>
        <textarea placeholder="Full reply text..." value={qrForm.content} onChange={(e) => setQrForm({ ...qrForm, content: e.target.value })} rows={4}
          style={{ width: '100%', padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', resize: 'vertical' }} />
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <input type="text" placeholder="Category (optional)" value={qrForm.category} onChange={(e) => setQrForm({ ...qrForm, category: e.target.value })}
          style={{ flex: 1, padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }} />
        <input type="text" placeholder="Keywords: return,refund,exchange" value={qrForm.keywords} onChange={(e) => setQrForm({ ...qrForm, keywords: e.target.value })}
          style={{ flex: 1, padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }} />
      </div>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button onClick={async () => {
          const method = editingQR ? 'PATCH' : 'POST';
          const url = editingQR ? `/api/v1/quick-replies/${editingQR}` : '/api/v1/quick-replies/';
          await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(qrForm) });
          setShowQRForm(false); setEditingQR(null); loadQR();
        }} disabled={!qrForm.title || !qrForm.content}
          style={{ padding: '6px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer', opacity: (!qrForm.title || !qrForm.content) ? 0.4 : 1 }}>
          {editingQR ? 'Save' : 'Create'}
        </button>
        <button onClick={() => { setShowQRForm(false); setEditingQR(null); }}
          style={{ padding: '6px 16px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
      </div>
    </div>
  )}
</section>
```

### Edit: `frontend/src/lib/i18n.js`

Add keys to both en and tr:

English:
```javascript
qr_title: "Quick Reply Templates",
qr_subtitle: "Pre-written answers for common questions. AI uses these automatically.",
qr_add: "+ Add Template",
qr_no_templates: "No templates yet. Add common answers like return policy, shipping info, working hours.",
qr_used: "Used",
qr_times: "times",
qr_keywords: "Keywords",
qr_button: "Quick Replies",
```

Turkish:
```javascript
qr_title: "Hızlı Yanıt Şablonları",
qr_subtitle: "Sık sorulan sorular için hazır cevaplar. AI bunları otomatik kullanır.",
qr_add: "+ Şablon Ekle",
qr_no_templates: "Henüz şablon yok. İade politikası, kargo bilgisi, çalışma saatleri gibi yaygın cevaplar ekleyin.",
qr_used: "Kullanıldı",
qr_times: "kez",
qr_keywords: "Anahtar kelimeler",
qr_button: "Hızlı Yanıtlar",
```

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before quick replies"`
2. Apply changes. Delete .db if needed. Restart backend.
3. Test CRUD:
```bash
# Create
curl -X POST http://localhost:8000/api/v1/quick-replies/ \
  -H "Content-Type: application/json" \
  -d '{"title":"Return Policy","content":"You can return any product within 14 days of purchase. Please contact us with your order number and we will arrange the return.","keywords":"return,refund,exchange,iade","category":"policies"}'

# Create another
curl -X POST http://localhost:8000/api/v1/quick-replies/ \
  -H "Content-Type: application/json" \
  -d '{"title":"Shipping Info","content":"We ship across Turkey within 2-3 business days. Free shipping on orders above 500 TL. Track your order using the link we send via email.","keywords":"shipping,cargo,delivery,kargo,teslimat","category":"shipping"}'

# List
curl http://localhost:8000/api/v1/quick-replies/ | python3 -m json.tool

# Match
curl "http://localhost:8000/api/v1/quick-replies/match?q=how%20do%20I%20return" | python3 -m json.tool
```
4. Open Settings → see Quick Reply Templates section → create/edit/delete templates.
5. Open Conversations → open a conversation → click "Quick Replies" → see template list → click to copy.
6. Test AI uses templates: send "What is your return policy?" via Instagram → AI should use the exact template content.

## SUMMARY

NEW:
- backend/app/models/quick_reply.py
- backend/app/api/quick_replies.py

EDITED:
- backend/app/models/__init__.py (1 import)
- backend/app/main.py (2 lines)
- backend/app/api/instagram.py (quick replies added to LLM prompt)
- backend/app/api/messenger.py (same)
- backend/app/api/livechat.py (same)
- frontend/src/pages/ConversationsPage.jsx (quick reply button + panel)
- frontend/src/pages/SettingsPage.jsx (quick reply management section)
- frontend/src/lib/i18n.js (new keys)

## DO NOT
- ❌ DO NOT rewrite any file
- ❌ DO NOT push to git
- ❌ DO NOT touch persona builder, catalog, or voice features

## START NOW. Checkpoint first.
