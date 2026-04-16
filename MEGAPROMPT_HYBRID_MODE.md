# MASTER PROMPT: Multi-Agent Phase 2 — Assignment + Hybrid Mode

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before hybrid mode"`
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog, or channel webhook core logic.

## WHAT THIS DOES

3 features:

### Feature 1 — Conversation Assignment
- Conversations can be assigned to a specific agent (user)
- Auto-assignment: new conversations get assigned round-robin to active agents
- Manual assignment: supervisor/admin can reassign any conversation
- Agent dashboard: agents see only their assigned conversations

### Feature 2 — AI-Human Hybrid Mode
- 3 modes per conversation:
  - **AI Auto** (default): AI responds automatically, no human needed
  - **AI Suggest**: AI generates a reply but waits for agent to approve/edit before sending
  - **Human Only**: AI is paused, agent writes replies manually
- Mode can be changed per conversation or set globally in Settings

### Feature 3 — Auto-Escalation
- When intent_score >= 80: conversation auto-switches to "AI Suggest" mode (high value lead, human should review)
- When intent_score >= 95: notification to supervisor (ready to close deal)
- Configurable thresholds in Settings

## BACKEND CHANGES

### Edit: `backend/app/models/conversation_state.py`

Add these columns to ConversationState:

```python
assigned_to = Column(String, default="")  # user_id of assigned agent
response_mode = Column(String, default="ai_auto")  # "ai_auto", "ai_suggest", "human_only"
pending_reply = Column(Text, default="")  # AI's suggested reply waiting for approval (ai_suggest mode)
pending_product_ids = Column(JSON, default=list)  # product IDs in pending reply
escalated = Column(Boolean, default=False)
escalation_reason = Column(String, default="")
```

Add these imports if not present:
```python
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float, Boolean
```

### New file: `backend/app/services/assignment.py`

```python
"""Auto-assignment of conversations to agents (round-robin)."""

from sqlalchemy import select, func
from app.core.database import async_session
from app.models.user import User
from app.models.conversation_state import ConversationState


async def get_next_agent() -> str:
    """Get the agent with fewest active conversations for round-robin assignment."""
    async with async_session() as session:
        # Get all active agents
        result = await session.execute(
            select(User).where(User.is_active == True, User.role == "agent")
        )
        agents = result.scalars().all()

        if not agents:
            # No agents, try supervisors
            result = await session.execute(
                select(User).where(User.is_active == True, User.role == "supervisor")
            )
            agents = result.scalars().all()

        if not agents:
            return ""  # No one to assign to

        # Count active conversations per agent
        agent_loads = {}
        for agent in agents:
            conv_result = await session.execute(
                select(func.count()).where(
                    ConversationState.assigned_to == agent.id,
                    ConversationState.stage != "post_purchase",
                )
            )
            count = conv_result.scalar() or 0
            agent_loads[agent.id] = count

        # Return agent with fewest conversations
        return min(agent_loads, key=agent_loads.get)


async def auto_assign_conversation(sender_id: str):
    """Assign a conversation to the next available agent if not already assigned."""
    async with async_session() as session:
        result = await session.execute(
            select(ConversationState).where(ConversationState.sender_id == sender_id)
        )
        conv = result.scalar_one_or_none()

        if not conv or conv.assigned_to:
            return  # Already assigned or doesn't exist

        agent_id = await get_next_agent()
        if agent_id:
            conv.assigned_to = agent_id
            await session.commit()
            print(f"Auto-assigned {sender_id} to agent {agent_id}")
```

### New file: `backend/app/api/assignment.py`

```python
"""Conversation assignment API."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation_state import ConversationState
from app.models.user import User

router = APIRouter()


@router.post("/conversations/{conv_id}/assign")
async def assign_conversation(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Assign conversation to a user."""
    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    agent_id = body.get("agent_id", "")

    # Validate agent exists
    if agent_id:
        agent_result = await db.execute(select(User).where(User.id == agent_id))
        if not agent_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Agent not found")

    conv.assigned_to = agent_id
    conv.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "assigned", "assigned_to": agent_id}


@router.post("/conversations/{conv_id}/set-mode")
async def set_response_mode(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Set conversation response mode: ai_auto, ai_suggest, human_only."""
    mode = body.get("mode", "")
    if mode not in ("ai_auto", "ai_suggest", "human_only"):
        raise HTTPException(status_code=400, detail="Invalid mode")

    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    conv.response_mode = mode
    conv.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "mode_set", "mode": mode}


@router.post("/conversations/{conv_id}/approve-reply")
async def approve_reply(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Approve or edit the AI's pending reply (ai_suggest mode). Then send it."""
    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    # Use edited text if provided, otherwise use pending reply
    final_text = body.get("text", conv.pending_reply or "")
    if not final_text:
        raise HTTPException(status_code=400, detail="No reply text")

    # Send the reply via the appropriate channel
    sender_id = conv.sender_id
    channel = conv.channel

    if channel == "instagram":
        from app.api.instagram import send_reply
        await send_reply(sender_id, final_text)
    elif channel == "messenger":
        from app.api.messenger import send_messenger_reply
        await send_messenger_reply(sender_id, final_text)

    # Send product images if any
    product_ids = body.get("product_ids", conv.pending_product_ids or [])
    if product_ids:
        try:
            from app.core.database import async_session as asess
            from app.models.catalog_models import Product
            async with asess() as session:
                for pid in product_ids[:3]:
                    prod_result = await session.execute(select(Product).where(Product.id == pid))
                    prod = prod_result.scalar_one_or_none()
                    if prod and prod.image_url:
                        if channel == "instagram":
                            from app.api.instagram import send_instagram_image
                            await send_instagram_image(sender_id, prod.image_url)
                        elif channel == "messenger":
                            from app.api.messenger import send_messenger_image
                            await send_messenger_image(sender_id, prod.image_url)
        except Exception as e:
            print(f"Image send error: {e}")

    # Update conversation
    msgs = list(conv.messages or [])
    msgs.append({"role": "assistant", "content": final_text, "timestamp": datetime.utcnow().isoformat(), "sent_by": "human"})
    conv.messages = msgs
    conv.pending_reply = ""
    conv.pending_product_ids = []
    conv.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "sent"}


@router.post("/conversations/{conv_id}/send-manual")
async def send_manual_reply(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Send a manual reply (human_only mode)."""
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")

    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    sender_id = conv.sender_id
    channel = conv.channel

    if channel == "instagram":
        from app.api.instagram import send_reply
        await send_reply(sender_id, text)
    elif channel == "messenger":
        from app.api.messenger import send_messenger_reply
        await send_messenger_reply(sender_id, text)

    msgs = list(conv.messages or [])
    msgs.append({"role": "assistant", "content": text, "timestamp": datetime.utcnow().isoformat(), "sent_by": "human"})
    conv.messages = msgs
    conv.message_count = len(msgs)
    conv.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "sent"}
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.assignment import router as assignment_router
```

Add include_router:
```python
app.include_router(assignment_router, prefix="/api/v1", tags=["Assignment"])
```

### Edit: `backend/app/api/instagram.py`

Modify the webhook to respect response_mode. Find where the AI reply is generated. BEFORE calling the LLM, add:

```python
# Check response mode
response_mode = "ai_auto"
try:
    from app.core.database import async_session as asess
    from app.models.conversation_state import ConversationState as CS
    async with asess() as sess:
        conv_result = await sess.execute(select(CS).where(CS.sender_id == sender_id))
        conv_state = conv_result.scalar_one_or_none()
        if conv_state:
            response_mode = conv_state.response_mode or "ai_auto"
except Exception:
    pass

# If human_only mode, don't generate AI reply at all
if response_mode == "human_only":
    print(f"Human-only mode for {sender_id}, skipping AI reply")
    # Still save the incoming message
    # (the save_conversation function already handles this)
    return {"status": "ok"}
```

AFTER the AI reply is generated but BEFORE sending it, add:

```python
# If ai_suggest mode, save reply as pending instead of sending
if response_mode == "ai_suggest":
    try:
        async with asess() as sess:
            conv_result = await sess.execute(select(CS).where(CS.sender_id == sender_id))
            conv_state = conv_result.scalar_one_or_none()
            if conv_state:
                conv_state.pending_reply = reply_text
                conv_state.pending_product_ids = recommend_product_ids if recommend_product_ids else []
                await sess.commit()
        print(f"AI Suggest mode: saved pending reply for {sender_id}")
        return {"status": "ok"}
    except Exception as e:
        print(f"Pending save error: {e}")
        # Fall through to auto-send if save fails
```

Also, AFTER sending the reply and updating conversation state, add auto-escalation:

```python
# Auto-escalation based on intent score
try:
    async with asess() as sess:
        conv_result = await sess.execute(select(CS).where(CS.sender_id == sender_id))
        conv_state = conv_result.scalar_one_or_none()
        if conv_state and conv_state.intent_score >= 80 and conv_state.response_mode == "ai_auto":
            conv_state.response_mode = "ai_suggest"
            conv_state.escalated = True
            conv_state.escalation_reason = f"Intent score reached {conv_state.intent_score}"
            await sess.commit()
            print(f"Auto-escalated {sender_id}: score {conv_state.intent_score}")
except Exception as e:
    print(f"Escalation check error: {e}")
```

Also add auto-assignment after upsert_customer:
```python
from app.services.assignment import auto_assign_conversation
await auto_assign_conversation(sender_id)
```

Do the same changes in `backend/app/api/messenger.py` — add response_mode check, ai_suggest pending save, and auto-escalation. Same logic, same spots.

### Edit: `backend/app/api/conversations_api.py`

Add these fields to the serialized conversation output (in both list and get endpoints):

```python
"assigned_to": s.assigned_to or "",
"response_mode": s.response_mode or "ai_auto",
"pending_reply": s.pending_reply or "",
"pending_product_ids": s.pending_product_ids or [],
"escalated": s.escalated or False,
"escalation_reason": s.escalation_reason or "",
```

Add filter by assigned_to. In list_conversations, add parameter:

```python
assigned_to: Optional[str] = Query(None),
```

And filter:
```python
if assigned_to:
    states = [s for s in states if s.assigned_to == assigned_to]
```

## FRONTEND CHANGES

### Edit: `frontend/src/pages/ConversationsPage.jsx`

Add these controls to the conversation detail panel:

1. Add state for agents list:
```jsx
const [agents, setAgents] = useState([]);
useEffect(() => {
  authFetch('/api/v1/auth/users').then(r => r.ok ? r.json() : []).then(setAgents).catch(() => {});
}, []);
```

Import authFetch:
```jsx
import { authFetch, getUser } from '../lib/auth';
```

2. Add "My Conversations" toggle at the top of the page (before search bar):
```jsx
<div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
  <button
    onClick={() => setAssignedFilter('')}
    style={{
      padding: '6px 14px', fontSize: '0.8rem', borderRadius: '9999px',
      background: !assignedFilter ? '#000' : '#fff',
      color: !assignedFilter ? '#fff' : '#374151',
      border: '1px solid #e5e7eb', cursor: 'pointer',
    }}
  >All</button>
  <button
    onClick={() => setAssignedFilter(getUser()?.id || '')}
    style={{
      padding: '6px 14px', fontSize: '0.8rem', borderRadius: '9999px',
      background: assignedFilter === getUser()?.id ? '#000' : '#fff',
      color: assignedFilter === getUser()?.id ? '#fff' : '#374151',
      border: '1px solid #e5e7eb', cursor: 'pointer',
    }}
  >My Conversations</button>
</div>
```

Add state:
```jsx
const [assignedFilter, setAssignedFilter] = useState('');
```

Update loadConversations to include filter:
```jsx
if (assignedFilter) params += `${params ? '&' : '?'}assigned_to=${assignedFilter}`;
```

3. In the detail panel, add assignment + mode controls AFTER the details header:

```jsx
{/* Assignment & Mode */}
<div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
  <div style={{ flex: 1 }}>
    <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px' }}>ASSIGNED TO</div>
    <select
      value={detail.assigned_to || ''}
      onChange={async (e) => {
        await authFetch(`/api/v1/conversations/${detail.id}/assign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: e.target.value }),
        });
        openDetail(detail.id);
      }}
      style={{ width: '100%', padding: '4px 8px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.375rem', outline: 'none' }}
    >
      <option value="">Unassigned</option>
      {agents.map(a => <option key={a.id} value={a.id}>{a.display_name} ({a.role})</option>)}
    </select>
  </div>
  <div style={{ flex: 1 }}>
    <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px' }}>RESPONSE MODE</div>
    <select
      value={detail.response_mode || 'ai_auto'}
      onChange={async (e) => {
        await authFetch(`/api/v1/conversations/${detail.id}/set-mode`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: e.target.value }),
        });
        openDetail(detail.id);
      }}
      style={{
        width: '100%', padding: '4px 8px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.375rem', outline: 'none',
        background: detail.response_mode === 'human_only' ? '#fef2f2' : detail.response_mode === 'ai_suggest' ? '#eff6ff' : '#f0fdf4',
      }}
    >
      <option value="ai_auto">🤖 AI Auto</option>
      <option value="ai_suggest">🤖+👤 AI Suggest</option>
      <option value="human_only">👤 Human Only</option>
    </select>
  </div>
</div>

{detail.escalated && (
  <div style={{ padding: '0.5rem 0.75rem', background: '#fef3c7', borderRadius: '0.5rem', fontSize: '0.8rem', color: '#92400e', marginBottom: '1rem' }}>
    ⚠️ Escalated: {detail.escalation_reason}
  </div>
)}
```

4. Add pending reply approval panel (for ai_suggest mode). Insert BEFORE the conversation messages:

```jsx
{detail.pending_reply && (
  <div style={{ marginBottom: '1rem', padding: '1rem', border: '2px solid #3b82f6', borderRadius: '0.5rem', background: '#eff6ff' }}>
    <div style={{ fontSize: '0.75rem', color: '#2563eb', fontWeight: 600, marginBottom: '0.5rem' }}>🤖 AI SUGGESTED REPLY (waiting for approval)</div>
    <textarea
      id="pending-reply-text"
      defaultValue={detail.pending_reply}
      rows={3}
      style={{ width: '100%', padding: '8px', border: '1px solid #bfdbfe', borderRadius: '0.375rem', fontSize: '0.85rem', outline: 'none', resize: 'vertical', marginBottom: '0.5rem', boxSizing: 'border-box' }}
    />
    <div style={{ display: 'flex', gap: '0.5rem' }}>
      <button
        onClick={async () => {
          const text = document.getElementById('pending-reply-text').value;
          await authFetch(`/api/v1/conversations/${detail.id}/approve-reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, product_ids: detail.pending_product_ids }),
          });
          openDetail(detail.id);
        }}
        style={{ padding: '6px 16px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}
      >✓ Approve & Send</button>
      <button
        onClick={async () => {
          await authFetch(`/api/v1/conversations/${detail.id}/approve-reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: detail.pending_reply, product_ids: detail.pending_product_ids }),
          });
          openDetail(detail.id);
        }}
        style={{ padding: '6px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}
      >Send as-is</button>
      <button
        onClick={async () => {
          // Discard: clear pending reply
          await authFetch(`/api/v1/conversations/${detail.id}/set-mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'human_only' }),
          });
          openDetail(detail.id);
        }}
        style={{ padding: '6px 16px', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}
      >Discard & Go Manual</button>
    </div>
  </div>
)}
```

5. Add manual reply input for human_only mode. Insert AFTER the conversation messages:

```jsx
{(detail.response_mode === 'human_only' || detail.response_mode === 'ai_suggest') && (
  <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
    <input
      type="text"
      id="manual-reply-input"
      placeholder="Type a reply..."
      onKeyDown={async (e) => {
        if (e.key === 'Enter') {
          const text = e.target.value.trim();
          if (!text) return;
          await authFetch(`/api/v1/conversations/${detail.id}/send-manual`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
          });
          e.target.value = '';
          openDetail(detail.id);
        }
      }}
      style={{ flex: 1, padding: '8px 14px', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.85rem', outline: 'none' }}
    />
    <button
      onClick={async () => {
        const input = document.getElementById('manual-reply-input');
        const text = input.value.trim();
        if (!text) return;
        await authFetch(`/api/v1/conversations/${detail.id}/send-manual`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        });
        input.value = '';
        openDetail(detail.id);
      }}
      style={{ padding: '8px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}
    >Send</button>
  </div>
)}
```

### Edit: `frontend/src/lib/i18n.js`

Add keys:

English:
```javascript
conv_assigned_to: "ASSIGNED TO",
conv_unassigned: "Unassigned",
conv_response_mode: "RESPONSE MODE",
conv_ai_auto: "AI Auto",
conv_ai_suggest: "AI Suggest",
conv_human_only: "Human Only",
conv_pending_reply: "AI SUGGESTED REPLY (waiting for approval)",
conv_approve_send: "Approve & Send",
conv_send_as_is: "Send as-is",
conv_discard_manual: "Discard & Go Manual",
conv_type_reply: "Type a reply...",
conv_send: "Send",
conv_my_conversations: "My Conversations",
conv_escalated: "Escalated",
```

Turkish:
```javascript
conv_assigned_to: "ATANAN",
conv_unassigned: "Atanmamış",
conv_response_mode: "YANIT MODU",
conv_ai_auto: "AI Otomatik",
conv_ai_suggest: "AI Öneri",
conv_human_only: "Sadece İnsan",
conv_pending_reply: "AI ÖNERİSİ (onay bekliyor)",
conv_approve_send: "Onayla ve Gönder",
conv_send_as_is: "Olduğu Gibi Gönder",
conv_discard_manual: "İptal Et & Manuel Geç",
conv_type_reply: "Bir yanıt yazın...",
conv_send: "Gönder",
conv_my_conversations: "Konuşmalarım",
conv_escalated: "Yönlendirildi",
```

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before hybrid mode"`
2. Apply. Delete .db if new columns needed. Restart backend. Re-create persona + catalog.
3. Register as admin. Add an agent user.
4. Test auto-assignment: send an Instagram DM → check conversation → should be assigned to the agent.
5. Test AI Auto mode (default): message comes in → AI auto-responds (as before).
6. Test AI Suggest mode: set a conversation to "AI Suggest" → send another DM → AI does NOT send reply → instead, pending reply appears in blue box in the detail panel → click "Approve & Send" → reply goes to customer.
7. Test Human Only: set to "Human Only" → send DM → no AI reply → type in the manual reply input → click Send → customer gets your message.
8. Test auto-escalation: have a conversation reach intent score 80+ → mode should auto-switch to "AI Suggest".
9. Test "My Conversations" filter → only shows conversations assigned to current user.

## SUMMARY

NEW:
- backend/app/services/assignment.py
- backend/app/api/assignment.py

EDITED:
- backend/app/models/conversation_state.py (5 new columns)
- backend/app/main.py (2 lines)
- backend/app/api/instagram.py (response mode check + ai_suggest pending + auto-escalation + auto-assign)
- backend/app/api/messenger.py (same)
- backend/app/api/conversations_api.py (new fields + assigned_to filter)
- frontend/src/pages/ConversationsPage.jsx (assignment dropdown + mode selector + pending approval + manual reply + my conversations filter)
- frontend/src/lib/i18n.js (new keys)

## DO NOT
- ❌ DO NOT rewrite any file
- ❌ DO NOT push to git
- ❌ DO NOT touch persona, catalog, voice, analytics

## START NOW. Checkpoint first.
