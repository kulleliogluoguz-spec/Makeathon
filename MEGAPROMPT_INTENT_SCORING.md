# MASTER PROMPT: Intent Scoring + Conversation Dashboard

## CRITICAL RULES

1. This is ADDITIVE. Do NOT rewrite existing files.
2. Run `git add -A && git commit -m "checkpoint before intent scoring"` FIRST as a safety checkpoint.
3. Do NOT push to git at any point.
4. Do NOT modify the frontend layout, existing pages, or styling. Only ADD a new page.
5. Do NOT touch the voice builder, voice picker, persona form, or catalog manager.

## WHAT THIS FEATURE DOES

After every Instagram DM, the backend analyzes the conversation and scores:
- **intent_score** (0-100): how close this customer is to making a purchase
- **stage** (awareness / interest / consideration / decision / purchase / objection / post_purchase)
- **signals**: specific behaviors detected (asked price, asked shipping, mentioned budget, compared products, showed urgency, etc.)
- **next_action**: strategic recommendation (provide info / send pricing / create urgency / ask for commitment / transfer to human)
- **breakdown**: 1-2 sentence explanation of why this score

The AI uses this context in its next reply — high-intent customers get more assertive, commitment-focused replies; low-intent customers get nurturing, informative replies.

A new "Conversations" dashboard shows all active conversations with intent scores, stages, and full history.

## BACKEND — NEW FILES

### File 1: `backend/app/models/conversation_state.py` (NEW)

```python
"""Conversation state tracking — per-customer intent scoring."""

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(String, primary_key=True, default=gen_uuid)
    sender_id = Column(String, nullable=False, index=True, unique=True)  # Instagram sender ID
    persona_id = Column(String, nullable=True, index=True)
    channel = Column(String, default="instagram")  # for future: whatsapp, voice, etc.

    # Current scoring snapshot
    intent_score = Column(Integer, default=0)
    stage = Column(String, default="awareness")
    signals = Column(JSON, default=list)
    next_action = Column(String, default="")
    score_breakdown = Column(Text, default="")

    # History of score changes (for timeline)
    score_history = Column(JSON, default=list)  # [{timestamp, score, stage, trigger_message}]

    # Message history (full transcript for dashboard)
    messages = Column(JSON, default=list)  # [{role, content, timestamp}]

    # Metadata
    message_count = Column(Integer, default=0)
    products_mentioned = Column(JSON, default=list)  # product IDs mentioned
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.conversation_state import ConversationState  # noqa
```

### File 2: `backend/app/services/intent_scorer.py` (NEW)

```python
"""Intent scoring using gpt-4.1-nano. Analyzes conversation and returns structured scoring data."""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


SCORING_SYSTEM_PROMPT = """You are a sales conversation analyst. Analyze the conversation between a customer and a business AI assistant, and score the customer's purchase intent.

Return a JSON object with EXACTLY these fields:

{
  "intent_score": integer 0-100,
  "stage": one of "awareness" | "interest" | "consideration" | "decision" | "purchase" | "objection" | "post_purchase",
  "signals": array of short strings describing what the customer has done (e.g. "asked about pricing", "mentioned budget", "asked about shipping", "showed urgency", "compared two products"),
  "next_action": one of "provide_info" | "send_pricing" | "send_product_images" | "create_urgency" | "ask_for_commitment" | "handle_objection" | "nurture" | "transfer_to_human",
  "score_breakdown": 1-2 sentence explanation of why you gave this score,
  "recommended_tone": one of "informative" | "enthusiastic" | "consultative" | "assertive" | "empathetic" | "urgent"
}

SCORING GUIDE:
- 0-20: Just browsing, vague questions, no clear product interest
- 21-40: Showing curiosity, asking general questions, early exploration
- 41-60: Active interest, asking about specific products or features, comparing options
- 61-80: Serious consideration, asking about price/shipping/availability, showing buying signals
- 81-100: Ready to buy, asking about checkout/payment/delivery logistics, high urgency

STAGE DEFINITIONS:
- awareness: just discovered the business, general questions
- interest: asking about specific products or categories
- consideration: comparing options, asking detailed questions about features
- decision: asking about price, availability, shipping, warranty
- purchase: ready to transact, asking how to buy
- objection: hesitating, raising concerns (price too high, wrong fit, etc.)
- post_purchase: already bought, follow-up questions

Return ONLY valid JSON, no other text."""


async def score_conversation(messages: list, products_mentioned: list = None) -> dict:
    """Score a conversation based on message history.
    messages: [{role: 'user' | 'assistant', content: str}]
    Returns dict with intent_score, stage, signals, next_action, score_breakdown, recommended_tone
    """
    if not OPENAI_API_KEY or not messages:
        return {
            "intent_score": 0,
            "stage": "awareness",
            "signals": [],
            "next_action": "provide_info",
            "score_breakdown": "Not enough data",
            "recommended_tone": "informative",
        }

    # Limit to last 20 messages
    recent = messages[-20:] if len(messages) > 20 else messages

    transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])

    context = ""
    if products_mentioned:
        context = f"\n\nProducts mentioned in conversation: {', '.join(products_mentioned[:10])}"

    user_message = f"Analyze this conversation and return the JSON scoring:\n\n{transcript}{context}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [
                        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 600,
                    "response_format": {"type": "json_object"},
                },
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        # Validate and sanitize
        return {
            "intent_score": max(0, min(100, int(parsed.get("intent_score", 0)))),
            "stage": parsed.get("stage", "awareness"),
            "signals": parsed.get("signals", [])[:10],
            "next_action": parsed.get("next_action", "provide_info"),
            "score_breakdown": parsed.get("score_breakdown", "")[:500],
            "recommended_tone": parsed.get("recommended_tone", "informative"),
        }
    except Exception as e:
        print(f"Intent scoring error: {e}")
        return {
            "intent_score": 0,
            "stage": "awareness",
            "signals": [],
            "next_action": "provide_info",
            "score_breakdown": f"Scoring failed: {e}",
            "recommended_tone": "informative",
        }
```

### File 3: `backend/app/api/conversations_api.py` (NEW)

```python
"""Conversations dashboard API - list and view conversation states."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.conversation_state import ConversationState

router = APIRouter()


@router.get("/conversations/")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations ordered by most recent activity."""
    result = await db.execute(
        select(ConversationState).order_by(desc(ConversationState.last_message_at))
    )
    states = result.scalars().all()
    return [
        {
            "id": s.id,
            "sender_id": s.sender_id,
            "persona_id": s.persona_id,
            "channel": s.channel,
            "intent_score": s.intent_score,
            "stage": s.stage,
            "signals": s.signals or [],
            "next_action": s.next_action,
            "score_breakdown": s.score_breakdown,
            "message_count": s.message_count,
            "products_mentioned": s.products_mentioned or [],
            "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in states
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get full details of a single conversation including messages and score history."""
    result = await db.execute(
        select(ConversationState).where(ConversationState.id == conversation_id)
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": state.id,
        "sender_id": state.sender_id,
        "persona_id": state.persona_id,
        "channel": state.channel,
        "intent_score": state.intent_score,
        "stage": state.stage,
        "signals": state.signals or [],
        "next_action": state.next_action,
        "score_breakdown": state.score_breakdown,
        "score_history": state.score_history or [],
        "messages": state.messages or [],
        "message_count": state.message_count,
        "products_mentioned": state.products_mentioned or [],
        "last_message_at": state.last_message_at.isoformat() if state.last_message_at else None,
        "created_at": state.created_at.isoformat() if state.created_at else None,
    }
```

### Edit: `backend/app/main.py`

Add this import near other router imports:
```python
from app.api.conversations_api import router as conversations_api_router
```

Add this line near other include_router calls:
```python
app.include_router(conversations_api_router, prefix="/api/v1", tags=["Conversations"])
```

### Edit: `backend/app/api/instagram.py`

Make these changes to integrate scoring into the webhook flow:

1. Add these imports at the top:
```python
from datetime import datetime
from app.services.intent_scorer import score_conversation
from app.core.database import async_session
from app.models.conversation_state import ConversationState
from sqlalchemy import select
```

2. Add this helper function (alongside the other helpers in the file):

```python
async def load_or_create_conversation_state(sender_id: str, persona_id: str = None):
    """Load existing ConversationState or create new one."""
    async with async_session() as session:
        result = await session.execute(
            select(ConversationState).where(ConversationState.sender_id == sender_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            state = ConversationState(
                sender_id=sender_id,
                persona_id=persona_id,
                channel="instagram",
                messages=[],
                score_history=[],
                signals=[],
                products_mentioned=[],
            )
            session.add(state)
            await session.commit()
            await session.refresh(state)
        return state.id, state.messages or [], state.products_mentioned or []


async def update_conversation_state(
    sender_id: str,
    new_messages: list,
    scoring: dict,
    products_added: list = None,
):
    """Append new messages, update scoring, append to score history."""
    async with async_session() as session:
        result = await session.execute(
            select(ConversationState).where(ConversationState.sender_id == sender_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            return

        # Append messages
        existing_messages = list(state.messages or [])
        for m in new_messages:
            existing_messages.append({
                "role": m["role"],
                "content": m["content"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        state.messages = existing_messages[-100:]  # keep last 100

        # Update scoring snapshot
        state.intent_score = scoring.get("intent_score", 0)
        state.stage = scoring.get("stage", "awareness")
        state.signals = scoring.get("signals", [])
        state.next_action = scoring.get("next_action", "")
        state.score_breakdown = scoring.get("score_breakdown", "")

        # Append to score history
        history = list(state.score_history or [])
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "intent_score": scoring.get("intent_score", 0),
            "stage": scoring.get("stage", "awareness"),
            "trigger_message": (new_messages[-1]["content"] if new_messages else "")[:200],
        })
        state.score_history = history[-50:]  # keep last 50

        # Update product mentions
        if products_added:
            existing = list(state.products_mentioned or [])
            for p in products_added:
                if p not in existing:
                    existing.append(p)
            state.products_mentioned = existing[-50:]

        state.message_count = (state.message_count or 0) + len(new_messages)
        state.last_message_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()

        await session.commit()
```

3. Modify the existing `get_reply` function. AFTER the persona and products are loaded, BEFORE calling the LLM for the reply, ADD:

```python
# Load conversation state
state_id, state_messages, state_products = await load_or_create_conversation_state(sender_id, persona.id if persona else None)

# Score the conversation based on existing messages + current user message
scoring_messages = state_messages + [{"role": "user", "content": user_message}]
scoring = await score_conversation(scoring_messages, state_products)

# Build scoring context for the persona reply
scoring_context = f"""

## CURRENT CUSTOMER STATE (use this to tailor your reply)
Intent Score: {scoring['intent_score']}/100
Stage: {scoring['stage']}
Recommended tone: {scoring['recommended_tone']}
Next action: {scoring['next_action']}
Signals detected: {', '.join(scoring['signals']) if scoring['signals'] else 'none yet'}
Analysis: {scoring['score_breakdown']}

STRATEGY BASED ON SCORE:
- If score 0-20: be welcoming and informative, introduce the business, ask what they're looking for
- If score 21-40: show interest in their needs, offer relevant product categories, be consultative
- If score 41-60: actively recommend specific products, send images, highlight features and benefits
- If score 61-80: address specifics (price, availability, shipping), create gentle urgency, ask for commitment softly
- If score 81-100: focus on closing — ask for the order, explain checkout, remove friction, be direct
- If stage is "objection": acknowledge their concern, address it directly with facts, reassure them
"""
```

Then add `scoring_context` to the LLM's system prompt alongside the product catalog context:

```python
full_system_prompt = system_prompt + products_text + scoring_context
```

4. AFTER the reply is generated and sent via Instagram, call `update_conversation_state`:

```python
await update_conversation_state(
    sender_id=sender_id,
    new_messages=[
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply_text},
    ],
    scoring=scoring,
    products_added=recommend_product_ids if recommend_product_ids else [],
)
```

Do NOT change anything else in instagram.py. Do not rewrite the reply-generation flow — only add the scoring load before LLM call and the state update after reply is sent.

## FRONTEND — NEW FILES ONLY

### New file: `frontend/src/pages/ConversationsPage.jsx`

```jsx
import { useState, useEffect } from 'react';

const STAGE_COLORS = {
  awareness: '#94a3b8',
  interest: '#3b82f6',
  consideration: '#8b5cf6',
  decision: '#f59e0b',
  purchase: '#10b981',
  objection: '#ef4444',
  post_purchase: '#06b6d4',
};

const STAGE_LABELS = {
  awareness: 'Awareness',
  interest: 'Interest',
  consideration: 'Considering',
  decision: 'Deciding',
  purchase: 'Ready to Buy',
  objection: 'Objection',
  post_purchase: 'Post-Purchase',
};

function ScoreGauge({ score }) {
  const color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#64748b';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ width: '60px', height: '6px', background: '#e5e7eb', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: '0.875rem', fontWeight: 600, color, minWidth: '36px' }}>{score}</span>
    </div>
  );
}

function StageBadge({ stage }) {
  const color = STAGE_COLORS[stage] || '#64748b';
  return (
    <span style={{
      fontSize: '0.75rem',
      fontWeight: 500,
      padding: '2px 10px',
      borderRadius: '9999px',
      background: color + '20',
      color: color,
    }}>
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadConversations = async () => {
    try {
      const resp = await fetch('/api/v1/conversations/');
      const data = await resp.json();
      setConversations(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const openDetail = async (id) => {
    setSelected(id);
    try {
      const resp = await fetch(`/api/v1/conversations/${id}`);
      const data = await resp.json();
      setDetail(data);
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>Conversations</h1>
      <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' }}>
        Live view of all customer conversations with intent scoring
      </p>

      {loading ? (
        <div style={{ color: '#9ca3af' }}>Loading...</div>
      ) : conversations.length === 0 ? (
        <div style={{ color: '#9ca3af', padding: '3rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.75rem' }}>
          No conversations yet. When customers DM your Instagram, they will appear here.
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '2rem' }}>
          {/* List */}
          <div style={{ flex: '1', maxWidth: '500px' }}>
            {conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => openDetail(c.id)}
                style={{
                  padding: '1rem',
                  border: '1px solid',
                  borderColor: selected === c.id ? '#000' : '#e5e7eb',
                  borderRadius: '0.75rem',
                  marginBottom: '0.75rem',
                  cursor: 'pointer',
                  background: '#fff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                      {c.channel === 'instagram' ? '📷' : '💬'} {c.sender_id.slice(0, 12)}...
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                      {c.message_count} messages · {new Date(c.last_message_at).toLocaleString()}
                    </div>
                  </div>
                  <StageBadge stage={c.stage} />
                </div>
                <ScoreGauge score={c.intent_score} />
                {c.signals && c.signals.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {c.signals.slice(0, 3).map((s, i) => (
                      <span key={i} style={{ fontSize: '0.7rem', padding: '2px 6px', background: '#f3f4f6', borderRadius: '4px', color: '#4b5563' }}>
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Detail */}
          <div style={{ flex: '1.3' }}>
            {!detail ? (
              <div style={{ color: '#9ca3af', padding: '2rem', textAlign: 'center' }}>
                Select a conversation to view details
              </div>
            ) : (
              <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#fff', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Details</h2>
                  <StageBadge stage={detail.stage} />
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>INTENT SCORE</div>
                  <ScoreGauge score={detail.intent_score} />
                  <div style={{ fontSize: '0.875rem', color: '#374151', marginTop: '0.75rem' }}>
                    {detail.score_breakdown}
                  </div>
                </div>

                {detail.signals && detail.signals.length > 0 && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>SIGNALS</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {detail.signals.map((s, i) => (
                        <span key={i} style={{ fontSize: '0.75rem', padding: '4px 10px', background: '#f3f4f6', borderRadius: '9999px', color: '#374151' }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>NEXT ACTION</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                    {detail.next_action.replace(/_/g, ' ')}
                  </div>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>CONVERSATION ({detail.messages?.length || 0} msgs)</div>
                  <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.75rem' }}>
                    {(detail.messages || []).map((m, i) => (
                      <div key={i} style={{
                        marginBottom: '0.75rem',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '0.5rem',
                        background: m.role === 'user' ? '#f3f4f6' : '#eff6ff',
                        fontSize: '0.875rem',
                      }}>
                        <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px' }}>
                          {m.role === 'user' ? 'CUSTOMER' : 'AI'}
                        </div>
                        {m.content}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

### Edit: `frontend/src/App.jsx`

Add a new route for the Conversations page. Make ONLY these minimal changes:

1. Add import at the top with other imports:
```jsx
import ConversationsPage from './pages/ConversationsPage';
```

2. Find the routing section (where other Routes are defined). Add ONE new route:
```jsx
<Route path="/conversations" element={<ConversationsPage />} />
```

3. Find the top navigation bar where links like "Personas" and "Agents" are rendered. Add ONE new link/tab:
```jsx
<Link to="/conversations" style={{ /* same style as existing links */ }}>Conversations</Link>
```

If the navbar uses styled components or Tailwind, match the existing pattern. DO NOT restructure the navbar — only add the new link next to existing ones.

DO NOT change any other file. DO NOT rewrite App.jsx.

## TEST PLAN

1. Commit checkpoint: `git add -A && git commit -m "checkpoint before intent scoring"`

2. Apply all changes, restart backend.

3. Verify endpoint:
```bash
curl http://localhost:8000/api/v1/conversations/
# Should return: []
```

4. Send a DM to @big.m.ai on Instagram asking about products.

5. Check conversation was created:
```bash
curl http://localhost:8000/api/v1/conversations/ | python3 -m json.tool
# Should show one conversation with intent_score, stage, etc.
```

6. Send a more committal message ("How much is it? Can you ship to Germany?"). Check score increases:
```bash
curl http://localhost:8000/api/v1/conversations/ | python3 -m json.tool
```

7. Open frontend at http://localhost:5173/conversations — see the conversation in the dashboard with score, stage, and full message history.

8. Verify the AI response adapts — a customer at score 70+ should get more assertive replies (asking for the order, providing specifics) than at score 20.

## SUMMARY OF FILES

NEW:
- backend/app/models/conversation_state.py
- backend/app/services/intent_scorer.py
- backend/app/api/conversations_api.py
- frontend/src/pages/ConversationsPage.jsx

EDITED (minimal additions only):
- backend/app/models/__init__.py (1 import line)
- backend/app/main.py (2 lines — import + include_router)
- backend/app/api/instagram.py (imports + 2 helper functions + scoring integration in get_reply)
- frontend/src/App.jsx (1 import + 1 Route + 1 Link)

## DO NOT

- ❌ DO NOT rewrite any existing file
- ❌ DO NOT modify existing pages or components
- ❌ DO NOT change layout, styling, or navbar structure
- ❌ DO NOT touch voice builder, voice picker, persona form, or catalog manager
- ❌ DO NOT push to git

## START NOW

1. `git add -A && git commit -m "checkpoint before intent scoring"`
2. Create the 4 new files
3. Make the minimal edits listed above
4. Restart backend
5. Test with a DM

Once working, tell the user to send several test DMs and watch the dashboard update in real-time.
