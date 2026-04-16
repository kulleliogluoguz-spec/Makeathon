# MASTER PROMPT: CSAT Survey System

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before csat"` as safety checkpoint.
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog manager, or existing page layouts.

## WHAT THIS DOES

After a conversation goes inactive for a configurable time (default: 30 min), the system sends a CSAT survey to the customer asking them to rate 1-5 stars. The rating is saved and shown in:
- Conversation detail panel
- Customer detail
- Analytics dashboard (new CSAT section)

Works across all channels: Instagram, Messenger, LiveChat.

## BACKEND

### New file: `backend/app/models/csat.py`

```python
"""CSAT survey responses."""

from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class CSATResponse(Base):
    __tablename__ = "csat_responses"

    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, nullable=False, index=True)
    sender_id = Column(String, nullable=False, index=True)
    channel = Column(String, default="")
    rating = Column(Integer, nullable=False)  # 1-5
    feedback = Column(Text, default="")  # optional text feedback
    created_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.csat import CSATResponse  # noqa
```

### New file: `backend/app/api/csat.py`

```python
"""CSAT survey API — send surveys and collect ratings."""

import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.models.csat import CSATResponse
from app.models.conversation_state import ConversationState

router = APIRouter()


@router.get("/csat/responses")
async def list_csat_responses(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
):
    """List all CSAT responses with optional time filter."""
    query = select(CSATResponse).order_by(desc(CSATResponse.created_at))

    if period == "today":
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)
        query = query.where(CSATResponse.created_at >= cutoff)
    elif period == "week":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=7))
    elif period == "month":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=30))

    result = await db.execute(query)
    responses = result.scalars().all()

    return [
        {
            "id": r.id,
            "conversation_id": r.conversation_id,
            "sender_id": r.sender_id,
            "channel": r.channel,
            "rating": r.rating,
            "feedback": r.feedback or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in responses
    ]


@router.get("/csat/stats")
async def get_csat_stats(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
):
    """Get CSAT statistics: average rating, distribution, response count."""
    query = select(CSATResponse)

    if period == "today":
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)
        query = query.where(CSATResponse.created_at >= cutoff)
    elif period == "week":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=7))
    elif period == "month":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=30))

    result = await db.execute(query)
    responses = result.scalars().all()

    total = len(responses)
    if total == 0:
        return {
            "total_responses": 0,
            "average_rating": 0,
            "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "satisfaction_rate": 0,
        }

    avg = round(sum(r.rating for r in responses) / total, 1)
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in responses:
        if 1 <= r.rating <= 5:
            dist[r.rating] += 1

    # Satisfaction rate = % of 4 and 5 star ratings
    satisfied = dist[4] + dist[5]
    sat_rate = round((satisfied / total) * 100, 1) if total > 0 else 0

    return {
        "total_responses": total,
        "average_rating": avg,
        "distribution": dist,
        "satisfaction_rate": sat_rate,
    }


@router.post("/csat/submit")
async def submit_csat(body: dict, db: AsyncSession = Depends(get_db)):
    """Submit a CSAT rating. Called by webhook handlers or livechat."""
    response = CSATResponse(
        conversation_id=body.get("conversation_id", ""),
        sender_id=body.get("sender_id", ""),
        channel=body.get("channel", ""),
        rating=max(1, min(5, int(body.get("rating", 3)))),
        feedback=body.get("feedback", ""),
    )
    db.add(response)
    await db.commit()
    return {"status": "submitted", "id": response.id}


@router.get("/csat/conversation/{conversation_id}")
async def get_conversation_csat(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get CSAT rating for a specific conversation."""
    result = await db.execute(
        select(CSATResponse)
        .where(CSATResponse.conversation_id == conversation_id)
        .order_by(desc(CSATResponse.created_at))
        .limit(1)
    )
    response = result.scalar_one_or_none()
    if not response:
        return {"has_rating": False}
    return {
        "has_rating": True,
        "rating": response.rating,
        "feedback": response.feedback or "",
        "created_at": response.created_at.isoformat() if response.created_at else None,
    }
```

### New file: `backend/app/services/csat_sender.py`

```python
"""Send CSAT survey messages to customers on each channel."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
MESSENGER_TOKEN = os.getenv("MESSENGER_PAGE_ACCESS_TOKEN", "")

SURVEY_MESSAGE = """How was your experience? Please rate us by replying with a number:

⭐ 1 — Very Unsatisfied
⭐⭐ 2 — Unsatisfied
⭐⭐⭐ 3 — Neutral
⭐⭐⭐⭐ 4 — Satisfied
⭐⭐⭐⭐⭐ 5 — Very Satisfied

Just reply with a number (1-5)!"""

SURVEY_MESSAGE_TR = """Deneyiminizi nasıl değerlendirirsiniz? Lütfen bir sayı ile yanıtlayın:

⭐ 1 — Çok Memnuniyetsiz
⭐⭐ 2 — Memnuniyetsiz
⭐⭐⭐ 3 — Nötr
⭐⭐⭐⭐ 4 — Memnun
⭐⭐⭐⭐⭐ 5 — Çok Memnun

Sadece bir sayı ile yanıtlayın (1-5)!"""


async def send_csat_survey(sender_id: str, channel: str, language: str = "en"):
    """Send CSAT survey message to the customer."""
    msg = SURVEY_MESSAGE_TR if language == "tr" else SURVEY_MESSAGE

    if channel == "instagram":
        await _send_instagram(sender_id, msg)
    elif channel == "messenger":
        await _send_messenger(sender_id, msg)
    # LiveChat: handled in frontend (widget shows rating UI)


async def _send_instagram(recipient_id: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {INSTAGRAM_TOKEN}", "Content-Type": "application/json"},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            print(f"CSAT Survey IG [{resp.status_code}]")
    except Exception as e:
        print(f"CSAT IG error: {e}")


async def _send_messenger(recipient_id: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {MESSENGER_TOKEN}", "Content-Type": "application/json"},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            print(f"CSAT Survey MSG [{resp.status_code}]")
    except Exception as e:
        print(f"CSAT MSG error: {e}")


def is_csat_response(text: str) -> int:
    """Check if a message is a CSAT rating response. Returns 0 if not, 1-5 if it is."""
    cleaned = text.strip()
    if cleaned in ("1", "2", "3", "4", "5"):
        return int(cleaned)
    return 0
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.csat import router as csat_router
```

Add include_router:
```python
app.include_router(csat_router, prefix="/api/v1", tags=["CSAT"])
```

### Edit: `backend/app/api/instagram.py`

Add CSAT rating detection to the Instagram webhook. At the top, add:
```python
from app.services.csat_sender import is_csat_response
from app.models.csat import CSATResponse
```

In the webhook POST handler, AFTER extracting the message text and BEFORE the business hours check, add:

```python
# Check if this is a CSAT rating response
csat_rating = is_csat_response(text)
if csat_rating > 0:
    try:
        from app.core.database import async_session
        from sqlalchemy import select
        from app.models.conversation_state import ConversationState

        async with async_session() as session:
            conv_result = await session.execute(
                select(ConversationState).where(ConversationState.sender_id == sender_id)
            )
            conv = conv_result.scalar_one_or_none()
            conv_id = conv.id if conv else ""

            csat = CSATResponse(
                conversation_id=conv_id,
                sender_id=sender_id,
                channel="instagram",
                rating=csat_rating,
            )
            session.add(csat)
            await session.commit()

        thank_msg = "Değerlendirmeniz için teşekkür ederiz! 🙏" if csat_rating >= 4 else "Geri bildiriminiz için teşekkür ederiz. Daha iyi olmak için çalışacağız! 🙏"
        await send_reply(sender_id, thank_msg)
        return {"status": "ok"}
    except Exception as e:
        print(f"CSAT save error: {e}")
```

This intercepts "1", "2", "3", "4", "5" messages and saves them as CSAT ratings instead of passing to the AI.

### Edit: `backend/app/api/messenger.py`

Add the exact same CSAT detection. At the top, add:
```python
from app.services.csat_sender import is_csat_response
from app.models.csat import CSATResponse
```

In the webhook POST handler, same spot as Instagram — after extracting text, before business hours check:

```python
# Check if this is a CSAT rating response
csat_rating = is_csat_response(text)
if csat_rating > 0:
    try:
        from app.core.database import async_session
        from sqlalchemy import select
        from app.models.conversation_state import ConversationState

        async with async_session() as session:
            conv_result = await session.execute(
                select(ConversationState).where(ConversationState.sender_id == sender_id)
            )
            conv = conv_result.scalar_one_or_none()
            conv_id = conv.id if conv else ""

            csat = CSATResponse(
                conversation_id=conv_id,
                sender_id=sender_id,
                channel="messenger",
                rating=csat_rating,
            )
            session.add(csat)
            await session.commit()

        thank_msg = "Thank you for your feedback! 🙏" if csat_rating >= 4 else "Thank you for your feedback. We'll work to improve! 🙏"
        await send_messenger_reply(sender_id, thank_msg)
        return {"status": "ok"}
    except Exception as e:
        print(f"CSAT save error: {e}")
```

### Edit: `backend/.env`

Add CSAT settings:
```
CSAT_ENABLED=true
CSAT_DELAY_MINUTES=30
```

## FRONTEND CHANGES

### Edit: `frontend/src/pages/ConversationsPage.jsx`

In the conversation detail panel, add CSAT display. Add state:
```jsx
const [csatData, setCsatData] = useState(null);
```

When a conversation detail is loaded (in the openDetail function), also fetch CSAT:
```jsx
const openDetail = async (id) => {
  setSelected(id);
  try {
    const resp = await fetch(`/api/v1/conversations/${id}`);
    const data = await resp.json();
    setDetail(data);

    // Fetch CSAT
    const csatResp = await fetch(`/api/v1/csat/conversation/${id}`);
    setCsatData(await csatResp.json());
  } catch (e) { console.error(e); }
};
```

In the detail panel, add a CSAT section AFTER the NEXT ACTION section and BEFORE the CONVERSATION section:

```jsx
{csatData && csatData.has_rating && (
  <div style={{ marginBottom: '1.5rem' }}>
    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>CUSTOMER RATING</div>
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      {[1, 2, 3, 4, 5].map(s => (
        <span key={s} style={{ fontSize: '1.25rem' }}>
          {s <= csatData.rating ? '⭐' : '☆'}
        </span>
      ))}
      <span style={{ marginLeft: '8px', fontSize: '0.875rem', fontWeight: 600 }}>
        {csatData.rating}/5
      </span>
    </div>
    {csatData.feedback && (
      <div style={{ fontSize: '0.8rem', color: '#374151', marginTop: '4px' }}>
        "{csatData.feedback}"
      </div>
    )}
  </div>
)}
```

### Edit: `frontend/src/pages/AnalyticsPage.jsx`

Add CSAT stats to the analytics page. Add state:
```jsx
const [csatStats, setCsatStats] = useState(null);
```

In the load function, add one more fetch to Promise.all:
```jsx
fetch(`/api/v1/csat/stats?${p}`).then(r => r.json()),
```

And assign it:
```jsx
// after the existing assignments in load():
setCsatStats(/* the csat result */);
```

IMPORTANT: Since Promise.all returns results in order, just add it as the 8th item and destructure accordingly.

Add a CSAT section in the analytics grid (inside the 2-column grid, add one more card):

```jsx
{/* CSAT */}
{csatStats && (
  <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
    <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Customer Satisfaction (CSAT)</h3>
    {csatStats.total_responses === 0 ? (
      <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No ratings yet</div>
    ) : (
      <div>
        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem' }}>
          <div>
            <div style={{ fontSize: '2rem', fontWeight: 600 }}>{csatStats.average_rating}</div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Average Rating</div>
          </div>
          <div>
            <div style={{ fontSize: '2rem', fontWeight: 600, color: '#10b981' }}>{csatStats.satisfaction_rate}%</div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Satisfaction Rate</div>
          </div>
          <div>
            <div style={{ fontSize: '2rem', fontWeight: 600 }}>{csatStats.total_responses}</div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Total Responses</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '80px' }}>
          {[1, 2, 3, 4, 5].map(star => {
            const count = csatStats.distribution[star] || 0;
            const max = Math.max(...Object.values(csatStats.distribution), 1);
            const pct = (count / max) * 100;
            const color = star >= 4 ? '#10b981' : star === 3 ? '#f59e0b' : '#ef4444';
            return (
              <div key={star} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '2px' }}>{count}</div>
                <div style={{ width: '100%', background: color, borderRadius: '4px 4px 0 0', height: `${Math.max(pct, 5)}%` }} />
                <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '4px' }}>{'⭐'.repeat(star)}</div>
              </div>
            );
          })}
        </div>
      </div>
    )}
  </div>
)}
```

### Add i18n keys to `frontend/src/lib/i18n.js`

Add these keys to BOTH en and tr translations:

English:
```javascript
csat_title: "Customer Satisfaction (CSAT)",
csat_avg_rating: "Average Rating",
csat_satisfaction_rate: "Satisfaction Rate",
csat_total_responses: "Total Responses",
csat_no_ratings: "No ratings yet",
csat_customer_rating: "CUSTOMER RATING",
```

Turkish:
```javascript
csat_title: "Müşteri Memnuniyeti (CSAT)",
csat_avg_rating: "Ortalama Puan",
csat_satisfaction_rate: "Memnuniyet Oranı",
csat_total_responses: "Toplam Değerlendirme",
csat_no_ratings: "Henüz değerlendirme yok",
csat_customer_rating: "MÜŞTERİ DEĞERLENDİRMESİ",
```

## SETTINGS — CSAT TOGGLE

### Edit: `frontend/src/pages/SettingsPage.jsx`

Add a CSAT section BEFORE the Live Chat Widget section:

```jsx
{/* CSAT Survey */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
    <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>CSAT Survey</h2>
    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', cursor: 'pointer' }}>
      <span style={{ fontWeight: 500 }}>Enabled</span>
      <input type="checkbox" defaultChecked style={{ width: '18px', height: '18px' }} />
    </label>
  </div>
  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
    After a conversation goes inactive, the system sends a satisfaction survey to the customer.
    They reply with 1-5 stars. Results appear in Analytics and Conversation details.
  </p>
  <p style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
    Currently active on: Instagram, Messenger. LiveChat widget shows rating UI automatically.
  </p>
</section>
```

## HOW IT WORKS END-TO-END

1. Customer chats with AI on Instagram/Messenger
2. Conversation goes quiet for 30+ minutes
3. System sends CSAT survey message ("Rate us 1-5!")
4. Customer replies "4"
5. Webhook detects it's a number 1-5 → saves as CSATResponse → sends thank you
6. Rating appears in conversation detail panel (⭐⭐⭐⭐)
7. Analytics shows average rating, distribution, satisfaction rate

Note: For now, the CSAT survey sending is manual (or can be triggered by a background job later). The priority is the RATING COLLECTION and DISPLAY. The auto-send after inactivity can be added as a cron job enhancement later.

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before csat"`
2. Apply changes. Restart backend. Delete .db if needed for new table.
3. Test API:
```bash
# Submit a test rating
curl -X POST http://localhost:8000/api/v1/csat/submit \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "test", "sender_id": "test", "channel": "instagram", "rating": 5}'

# Get stats
curl http://localhost:8000/api/v1/csat/stats | python3 -m json.tool
```
4. Test via Instagram: send "4" as a message → should get thank you reply instead of AI response.
5. Open /conversations → select a conversation → see CSAT rating if submitted.
6. Open /analytics → see CSAT section with average, distribution chart, satisfaction rate.

## SUMMARY

NEW:
- backend/app/models/csat.py
- backend/app/api/csat.py
- backend/app/services/csat_sender.py

EDITED:
- backend/app/models/__init__.py (1 import)
- backend/app/main.py (2 lines)
- backend/app/api/instagram.py (CSAT detection block)
- backend/app/api/messenger.py (CSAT detection block)
- frontend/src/pages/ConversationsPage.jsx (CSAT display in detail)
- frontend/src/pages/AnalyticsPage.jsx (CSAT stats section)
- frontend/src/pages/SettingsPage.jsx (CSAT toggle section)
- frontend/src/lib/i18n.js (6 new keys)

## DO NOT
- ❌ DO NOT rewrite any existing file
- ❌ DO NOT push to git
- ❌ DO NOT touch persona builder, catalog, or voice features

## START NOW. Checkpoint first.
