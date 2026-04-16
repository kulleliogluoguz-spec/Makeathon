# PROMPT: Advanced Message Search + PDF Export

## CRITICAL RULES
- Do NOT rewrite any existing file
- Do NOT push to git
- Do NOT touch persona builder, voice builder, catalog manager

## FEATURE 1 — CONVERSATION MESSAGE SEARCH

Users can search inside all conversations for a keyword (e.g. "fiyat", "iade", "tişört"). Returns matching conversations with the matching message highlighted.

### Edit: `backend/app/api/conversations_api.py`

Add a new search endpoint:

```python
@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Search inside all conversation messages for a keyword."""
    result = await db.execute(select(ConversationState).order_by(desc(ConversationState.last_message_at)))
    all_convs = result.scalars().all()

    matches = []
    query_lower = q.lower()

    for conv in all_convs:
        msgs = conv.messages or []
        matching_msgs = []
        for i, m in enumerate(msgs):
            if query_lower in (m.get("content", "") or "").lower():
                matching_msgs.append({
                    "index": i,
                    "role": m.get("role", ""),
                    "content": m.get("content", ""),
                    "timestamp": m.get("timestamp", ""),
                })

        if matching_msgs:
            matches.append({
                "conversation_id": conv.id,
                "sender_id": conv.sender_id,
                "channel": conv.channel,
                "intent_score": conv.intent_score,
                "stage": conv.stage,
                "categories": conv.categories or [],
                "message_count": conv.message_count,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "matching_messages": matching_msgs[:5],
                "total_matches": len(matching_msgs),
            })

    return {"query": q, "total_conversations": len(matches), "results": matches}
```

IMPORTANT: Place this endpoint BEFORE the `@router.get("/conversations/{conversation_id}")` endpoint in the file. Otherwise FastAPI will interpret "search" as a conversation_id.

### Edit: `frontend/src/pages/ConversationsPage.jsx`

Add a search bar and search results panel.

1. Add state:
```jsx
const [searchQuery, setSearchQuery] = useState('');
const [searchResults, setSearchResults] = useState(null);
const [searching, setSearching] = useState(false);
```

2. Add search function:
```jsx
const doSearch = async () => {
  if (!searchQuery.trim()) { setSearchResults(null); return; }
  setSearching(true);
  try {
    const resp = await fetch(`/api/v1/conversations/search?q=${encodeURIComponent(searchQuery)}`);
    setSearchResults(await resp.json());
  } catch (e) { console.error(e); }
  setSearching(false);
};
```

3. Insert a search bar BELOW the page title and description, ABOVE the tag filter bar:

```jsx
<div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
  <input
    type="text"
    placeholder="Search inside messages... (e.g. fiyat, iade, tişört)"
    value={searchQuery}
    onChange={(e) => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults(null); }}
    onKeyDown={(e) => { if (e.key === 'Enter') doSearch(); }}
    style={{
      flex: 1, padding: '0.5rem 1rem', fontSize: '0.875rem',
      border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
    }}
  />
  <button
    onClick={doSearch}
    disabled={searching}
    style={{
      padding: '0.5rem 1rem', background: '#000', color: '#fff',
      border: 'none', borderRadius: '9999px', fontSize: '0.875rem',
      cursor: searching ? 'wait' : 'pointer', opacity: searching ? 0.5 : 1,
    }}
  >{searching ? 'Searching...' : 'Search'}</button>
  {searchResults && (
    <button
      onClick={() => { setSearchResults(null); setSearchQuery(''); }}
      style={{
        padding: '0.5rem 1rem', background: '#fff', color: '#374151',
        border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
      }}
    >Clear</button>
  )}
</div>
```

4. When searchResults is not null, show search results INSTEAD of the normal conversation list. Add this block where the conversation list is rendered:

```jsx
{searchResults ? (
  <div>
    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
      Found "{searchResults.query}" in {searchResults.total_conversations} conversation(s)
    </div>
    {searchResults.results.map((r) => (
      <div
        key={r.conversation_id}
        onClick={() => openDetail(r.conversation_id)}
        style={{
          padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
          marginBottom: '0.75rem', cursor: 'pointer', background: '#fff',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>
            {r.channel === 'instagram' ? '📷' : '💬'} {r.sender_id.slice(0, 12)}...
          </span>
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
            {r.total_matches} match(es)
          </span>
        </div>
        {r.matching_messages.slice(0, 2).map((m, i) => (
          <div key={i} style={{
            padding: '0.5rem', background: m.role === 'user' ? '#f3f4f6' : '#eff6ff',
            borderRadius: '0.375rem', marginBottom: '0.25rem', fontSize: '0.8rem',
          }}>
            <span style={{ fontSize: '0.65rem', color: '#6b7280' }}>
              {m.role === 'user' ? 'CUSTOMER' : 'AI'}:
            </span>{' '}
            {highlightMatch(m.content, searchResults.query)}
          </div>
        ))}
      </div>
    ))}
  </div>
) : (
  /* existing conversation list stays here unchanged */
)}
```

5. Add the highlight helper function inside the component:

```jsx
const highlightMatch = (text, query) => {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  const before = text.slice(0, idx);
  const match = text.slice(idx, idx + query.length);
  const after = text.slice(idx + query.length);
  return (
    <>
      {before}<span style={{ background: '#fef08a', fontWeight: 600 }}>{match}</span>{after}
    </>
  );
};
```

Do NOT change the existing conversation list rendering. Just wrap it in the else branch of the searchResults conditional.

## FEATURE 2 — PDF EXPORT

Users can download a conversation's full chat history as a PDF.

### Add to backend requirements.txt (if not present):
```
reportlab==4.2.5
```

### New file: `backend/app/api/conversation_export.py`

```python
"""Export conversation as PDF."""

import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation_state import ConversationState

router = APIRouter()


@router.get("/conversations/{conversation_id}/export-pdf")
async def export_conversation_pdf(conversation_id: str, db: AsyncSession = Depends(get_db)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import mm

    result = await db.execute(
        select(ConversationState).where(ConversationState.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=HexColor("#6b7280"), spaceAfter=12)
    user_style = ParagraphStyle("User", parent=styles["Normal"], fontSize=10, backColor=HexColor("#f3f4f6"), borderPadding=6, spaceAfter=6, leftIndent=0)
    ai_style = ParagraphStyle("AI", parent=styles["Normal"], fontSize=10, backColor=HexColor("#eff6ff"), borderPadding=6, spaceAfter=6, leftIndent=0)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=8, textColor=HexColor("#6b7280"), spaceAfter=2)

    elements = []
    elements.append(Paragraph("Conversation Export", title_style))
    elements.append(Paragraph(
        f"Channel: {conv.channel} | Score: {conv.intent_score} | Stage: {conv.stage} | "
        f"Messages: {conv.message_count} | "
        f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        meta_style
    ))
    elements.append(Spacer(1, 6))

    for msg in (conv.messages or []):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")

        label = "CUSTOMER" if role == "user" else "AI ASSISTANT"
        time_str = f" — {ts}" if ts else ""
        elements.append(Paragraph(f"{label}{time_str}", label_style))

        safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        style = user_style if role == "user" else ai_style
        elements.append(Paragraph(safe_content, style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"conversation_{conv.sender_id[:8]}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.conversation_export import router as export_router
```

Add include_router:
```python
app.include_router(export_router, prefix="/api/v1", tags=["Export"])
```

### Edit: `frontend/src/pages/ConversationsPage.jsx`

In the conversation detail panel, find the CONVERSATION section header. Add a PDF download button next to it:

Find this line (or similar):
```jsx
<div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>CONVERSATION ({detail.messages?.length || 0} msgs)</div>
```

Replace it with:
```jsx
<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
    CONVERSATION ({detail.messages?.length || 0} msgs)
  </div>
  <button
    onClick={() => {
      window.open(`/api/v1/conversations/${detail.id}/export-pdf`, '_blank');
    }}
    style={{
      padding: '3px 10px', fontSize: '0.7rem', background: '#fff',
      border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
      color: '#374151',
    }}
  >📄 Export PDF</button>
</div>
```

## TEST PLAN

1. Restart backend (after `pip install reportlab`).

2. Test message search:
```bash
curl "http://localhost:8000/api/v1/conversations/search?q=merhaba" | python3 -m json.tool
```
Should return conversations containing "merhaba" with matching messages highlighted.

3. Test PDF export:
```bash
curl http://localhost:8000/api/v1/conversations/ | python3 -m json.tool | grep '"id"'
```
Take a conversation ID, then:
```bash
curl "http://localhost:8000/api/v1/conversations/CONV_ID/export-pdf" --output test.pdf
open test.pdf
```
Should open a formatted PDF with conversation history.

4. Frontend — Conversations page:
- Type a keyword in the search bar, press Enter → matching conversations appear with highlighted text
- Click Clear → back to normal list
- Open a conversation detail → click "Export PDF" → PDF downloads

## SUMMARY

NEW:
- backend/app/api/conversation_export.py

EDITED:
- backend/app/api/conversations_api.py (1 new search endpoint — place BEFORE the {id} endpoint)
- backend/app/main.py (2 lines)
- backend/requirements.txt (reportlab)
- frontend/src/pages/ConversationsPage.jsx (search bar + search results + PDF button)

## DO NOT
- ❌ DO NOT rewrite any file
- ❌ DO NOT push to git
- ❌ DO NOT touch other pages

## START NOW
