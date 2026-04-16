# MASTER PROMPT: Multi-Agent Phase 3 — Teams + Agent Performance + Supervisor Monitoring

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before teams"`
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog, or channel webhook core logic.

## WHAT THIS DOES

### Feature 1 — Departments / Teams
- Create teams: "Sales", "Support", "Technical", etc.
- Each team has members (agents/supervisors)
- New conversations can be routed to a TEAM instead of individual agent
- Team members see all team conversations
- Admin manages teams from /users (Team) page

### Feature 2 — Agent Performance Metrics
- Per-agent stats: conversations handled, avg response time, resolution count, CSAT average
- Shown in Team page and Analytics
- Time period filter (today/week/month)

### Feature 3 — Supervisor Live Monitoring
- Supervisor sees real-time conversation feed of their team's agents
- Can see what AI suggested vs what agent actually sent
- "Watching" indicator (optional)

## BACKEND — NEW FILES

### New file: `backend/app/models/team.py`

```python
"""Team/Department model."""

from sqlalchemy import Column, String, Text, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)  # "Sales", "Support", etc.
    description = Column(Text, default="")
    color = Column(String, default="#3b82f6")
    member_ids = Column(JSON, default=list)  # list of user IDs
    auto_assign_enabled = Column(String, default="true")  # round-robin within team
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.team import Team  # noqa
```

### Edit: `backend/app/models/conversation_state.py`

Add ONE column:
```python
assigned_team = Column(String, default="")  # team ID
```

### New file: `backend/app/api/teams.py`

```python
"""Team management API."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.team import Team
from app.models.user import User

router = APIRouter()


@router.get("/teams/")
async def list_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team))
    teams = result.scalars().all()
    return [_serialize(t) for t in teams]


@router.post("/teams/")
async def create_team(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(status_code=400, detail="Name required")
    team = Team(
        name=body["name"],
        description=body.get("description", ""),
        color=body.get("color", "#3b82f6"),
        member_ids=body.get("member_ids", []),
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return _serialize(team)


@router.patch("/teams/{team_id}")
async def update_team(team_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    for field in ("name", "description", "color", "member_ids", "auto_assign_enabled"):
        if field in body:
            setattr(team, field, body[field])
    team.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(team)
    return _serialize(team)


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    await db.delete(team)
    await db.commit()
    return {"status": "deleted"}


@router.post("/teams/{team_id}/members")
async def add_member(team_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Add a user to a team."""
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    user_id = body.get("user_id", "")
    if not user_id:
        raise HTTPException(status_code=400)
    members = list(team.member_ids or [])
    if user_id not in members:
        members.append(user_id)
    team.member_ids = members
    await db.commit()
    return {"status": "added", "members": members}


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_member(team_id: str, user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    members = list(team.member_ids or [])
    members = [m for m in members if m != user_id]
    team.member_ids = members
    await db.commit()
    return {"status": "removed", "members": members}


@router.get("/teams/{team_id}/conversations")
async def get_team_conversations(team_id: str, db: AsyncSession = Depends(get_db)):
    """Get all conversations assigned to this team or to team members."""
    from app.models.conversation_state import ConversationState
    from sqlalchemy import or_

    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)

    member_ids = team.member_ids or []

    conv_result = await db.execute(
        select(ConversationState).where(
            or_(
                ConversationState.assigned_team == team_id,
                ConversationState.assigned_to.in_(member_ids) if member_ids else False,
            )
        )
    )
    conversations = conv_result.scalars().all()

    return [
        {
            "id": c.id,
            "sender_id": c.sender_id,
            "channel": c.channel,
            "intent_score": c.intent_score,
            "stage": c.stage,
            "assigned_to": c.assigned_to or "",
            "response_mode": c.response_mode or "ai_auto",
            "message_count": c.message_count,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        }
        for c in conversations
    ]


def _serialize(t: Team) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description or "",
        "color": t.color or "#3b82f6",
        "member_ids": t.member_ids or [],
        "auto_assign_enabled": t.auto_assign_enabled == "true",
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
```

### New file: `backend/app/api/agent_performance.py`

```python
"""Agent performance metrics API."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.models.conversation_state import ConversationState
from app.models.csat import CSATResponse

router = APIRouter()


def get_cutoff(period: str):
    if period == "today":
        return datetime.utcnow().replace(hour=0, minute=0, second=0)
    elif period == "week":
        return datetime.utcnow() - timedelta(days=7)
    elif period == "month":
        return datetime.utcnow() - timedelta(days=30)
    return None


@router.get("/agent-performance/")
async def get_all_agent_performance(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Get performance metrics for all agents."""
    cutoff = get_cutoff(period)

    # Get all agents and supervisors
    user_result = await db.execute(
        select(User).where(User.role.in_(["agent", "supervisor", "admin"]))
    )
    users = user_result.scalars().all()

    # Get all conversations
    conv_query = select(ConversationState)
    if cutoff:
        conv_query = conv_query.where(ConversationState.last_message_at >= cutoff)
    conv_result = await db.execute(conv_query)
    all_convs = conv_result.scalars().all()

    # Get all CSAT
    csat_query = select(CSATResponse)
    if cutoff:
        csat_query = csat_query.where(CSATResponse.created_at >= cutoff)
    csat_result = await db.execute(csat_query)
    all_csat = csat_result.scalars().all()

    # Build per-user metrics
    metrics = []
    for user in users:
        user_convs = [c for c in all_convs if c.assigned_to == user.id]
        total_convs = len(user_convs)
        total_messages = sum(c.message_count or 0 for c in user_convs)

        # Resolved = stage is purchase or post_purchase
        resolved = sum(1 for c in user_convs if c.stage in ("purchase", "post_purchase"))

        # Average intent score
        avg_intent = round(sum(c.intent_score or 0 for c in user_convs) / max(total_convs, 1), 1)

        # CSAT for this agent's conversations
        conv_ids = {c.id for c in user_convs}
        user_csat = [r for r in all_csat if r.conversation_id in conv_ids]
        avg_csat = round(sum(r.rating for r in user_csat) / max(len(user_csat), 1), 1) if user_csat else 0

        # High intent conversations (score >= 70)
        high_intent = sum(1 for c in user_convs if (c.intent_score or 0) >= 70)

        # Active conversations (not archived, has recent messages)
        active = sum(1 for c in user_convs if c.stage not in ("post_purchase",))

        # Response modes
        ai_auto_count = sum(1 for c in user_convs if (c.response_mode or "ai_auto") == "ai_auto")
        ai_suggest_count = sum(1 for c in user_convs if c.response_mode == "ai_suggest")
        human_only_count = sum(1 for c in user_convs if c.response_mode == "human_only")

        metrics.append({
            "user_id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "total_conversations": total_convs,
            "total_messages": total_messages,
            "resolved_conversations": resolved,
            "active_conversations": active,
            "avg_intent_score": avg_intent,
            "high_intent_count": high_intent,
            "avg_csat": avg_csat,
            "csat_count": len(user_csat),
            "ai_auto_count": ai_auto_count,
            "ai_suggest_count": ai_suggest_count,
            "human_only_count": human_only_count,
        })

    # Sort by total conversations desc
    metrics.sort(key=lambda x: x["total_conversations"], reverse=True)
    return {"period": period, "agents": metrics}


@router.get("/agent-performance/{user_id}")
async def get_agent_detail(user_id: str, period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Get detailed performance for a single agent."""
    cutoff = get_cutoff(period)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    conv_query = select(ConversationState).where(ConversationState.assigned_to == user_id)
    if cutoff:
        conv_query = conv_query.where(ConversationState.last_message_at >= cutoff)
    conv_result = await db.execute(conv_query)
    convs = conv_result.scalars().all()

    # Channel breakdown
    channel_counts = {}
    stage_counts = {}
    for c in convs:
        ch = c.channel or "unknown"
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
        st = c.stage or "awareness"
        stage_counts[st] = stage_counts.get(st, 0) + 1

    return {
        "user": {
            "id": user.id,
            "display_name": user.display_name,
            "role": user.role,
        },
        "total_conversations": len(convs),
        "channel_breakdown": channel_counts,
        "stage_breakdown": stage_counts,
        "conversations": [
            {
                "id": c.id,
                "sender_id": c.sender_id,
                "channel": c.channel,
                "intent_score": c.intent_score,
                "stage": c.stage,
                "response_mode": c.response_mode,
                "message_count": c.message_count,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in convs[:50]
        ],
    }
```

### Edit: `backend/app/main.py`

Add imports:
```python
from app.api.teams import router as teams_router
from app.api.agent_performance import router as perf_router
```

Add include_routers:
```python
app.include_router(teams_router, prefix="/api/v1", tags=["Teams"])
app.include_router(perf_router, prefix="/api/v1", tags=["Performance"])
```

### Edit: `backend/app/services/assignment.py`

Update auto-assignment to consider teams. Replace the get_next_agent function:

```python
async def get_next_agent(team_id: str = "") -> str:
    """Get the agent with fewest active conversations. If team_id given, pick from that team only."""
    async with async_session() as session:
        if team_id:
            from app.models.team import Team
            team_result = await session.execute(select(Team).where(Team.id == team_id))
            team = team_result.scalar_one_or_none()
            if team and team.member_ids:
                result = await session.execute(
                    select(User).where(User.id.in_(team.member_ids), User.is_active == True)
                )
                agents = result.scalars().all()
                if agents:
                    agent_loads = {}
                    for agent in agents:
                        from sqlalchemy import func
                        conv_result = await session.execute(
                            select(func.count()).where(ConversationState.assigned_to == agent.id)
                        )
                        agent_loads[agent.id] = conv_result.scalar() or 0
                    return min(agent_loads, key=agent_loads.get)

        # Default: pick from all agents
        result = await session.execute(
            select(User).where(User.is_active == True, User.role == "agent")
        )
        agents = result.scalars().all()
        if not agents:
            result = await session.execute(
                select(User).where(User.is_active == True, User.role == "supervisor")
            )
            agents = result.scalars().all()
        if not agents:
            return ""

        agent_loads = {}
        for agent in agents:
            from sqlalchemy import func
            conv_result = await session.execute(
                select(func.count()).where(ConversationState.assigned_to == agent.id)
            )
            agent_loads[agent.id] = conv_result.scalar() or 0
        return min(agent_loads, key=agent_loads.get)
```

## FRONTEND CHANGES

### Edit: `frontend/src/pages/UsersPage.jsx`

Add Teams management section. Add state at top:

```jsx
const [teams, setTeams] = useState([]);
const [showTeamForm, setShowTeamForm] = useState(false);
const [teamForm, setTeamForm] = useState({ name: '', description: '', color: '#3b82f6' });
const [editingTeam, setEditingTeam] = useState(null);
const [performance, setPerformance] = useState(null);
const [perfPeriod, setPerfPeriod] = useState('month');

const loadTeams = async () => {
  try {
    const resp = await authFetch('/api/v1/teams/');
    if (resp.ok) setTeams(await resp.json());
  } catch (e) {}
};

const loadPerformance = async () => {
  try {
    const resp = await authFetch(`/api/v1/agent-performance/?period=${perfPeriod}`);
    if (resp.ok) setPerformance(await resp.json());
  } catch (e) {}
};

useEffect(() => { loadTeams(); loadPerformance(); }, [perfPeriod]);
```

Add Teams section AFTER the users list:

```jsx
{/* Teams */}
<div style={{ marginTop: '2.5rem' }}>
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
    <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Teams</h2>
    <button onClick={() => { setTeamForm({ name: '', description: '', color: '#3b82f6' }); setEditingTeam(null); setShowTeamForm(true); }}
      style={{ padding: '6px 14px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>+ Create Team</button>
  </div>

  {teams.map((team) => (
    <div key={team.id} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.75rem', background: '#fff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: team.color }} />
          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{team.name}</span>
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>{(team.member_ids || []).length} members</span>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={() => { setTeamForm({ name: team.name, description: team.description, color: team.color }); setEditingTeam(team.id); setShowTeamForm(true); }}
            style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Edit</button>
          <button onClick={async () => { if (confirm('Delete?')) { await authFetch(`/api/v1/teams/${team.id}`, { method: 'DELETE' }); loadTeams(); } }}
            style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
        </div>
      </div>
      {team.description && <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem' }}>{team.description}</div>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {(team.member_ids || []).map((uid) => {
          const u = users.find(x => x.id === uid);
          return u ? (
            <span key={uid} style={{ fontSize: '0.75rem', padding: '3px 10px', background: '#f3f4f6', borderRadius: '9999px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              {u.display_name}
              <button onClick={async () => { await authFetch(`/api/v1/teams/${team.id}/members/${uid}`, { method: 'DELETE' }); loadTeams(); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: '0.8rem' }}>×</button>
            </span>
          ) : null;
        })}
        <select
          onChange={async (e) => {
            if (!e.target.value) return;
            await authFetch(`/api/v1/teams/${team.id}/members`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: e.target.value }),
            });
            e.target.value = '';
            loadTeams();
          }}
          style={{ fontSize: '0.75rem', padding: '3px 8px', border: '1px dashed #e5e7eb', borderRadius: '9999px', outline: 'none', color: '#9ca3af' }}
        >
          <option value="">+ Add member</option>
          {users.filter(u => !(team.member_ids || []).includes(u.id)).map(u => (
            <option key={u.id} value={u.id}>{u.display_name}</option>
          ))}
        </select>
      </div>
    </div>
  ))}

  {showTeamForm && (
    <div style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#f9fafb', marginTop: '0.5rem' }}>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <input type="text" placeholder="Team name" value={teamForm.name} onChange={(e) => setTeamForm({ ...teamForm, name: e.target.value })}
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
        <input type="color" value={teamForm.color} onChange={(e) => setTeamForm({ ...teamForm, color: e.target.value })}
          style={{ width: '40px', height: '36px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', cursor: 'pointer' }} />
      </div>
      <input type="text" placeholder="Description (optional)" value={teamForm.description} onChange={(e) => setTeamForm({ ...teamForm, description: e.target.value })}
        style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', marginBottom: '0.75rem', boxSizing: 'border-box' }} />
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button onClick={async () => {
          const method = editingTeam ? 'PATCH' : 'POST';
          const url = editingTeam ? `/api/v1/teams/${editingTeam}` : '/api/v1/teams/';
          await authFetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(teamForm) });
          setShowTeamForm(false); loadTeams();
        }} style={{ padding: '6px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>
          {editingTeam ? 'Save' : 'Create'}</button>
        <button onClick={() => setShowTeamForm(false)}
          style={{ padding: '6px 16px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
      </div>
    </div>
  )}
</div>

{/* Agent Performance */}
{performance && (
  <div style={{ marginTop: '2.5rem' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Agent Performance</h2>
      <div style={{ display: 'flex', gap: '4px' }}>
        {['today', 'week', 'month'].map(p => (
          <button key={p} onClick={() => setPerfPeriod(p)}
            style={{
              padding: '4px 12px', fontSize: '0.75rem', borderRadius: '9999px',
              background: perfPeriod === p ? '#000' : '#fff', color: perfPeriod === p ? '#fff' : '#374151',
              border: '1px solid #e5e7eb', cursor: 'pointer',
            }}>{p.charAt(0).toUpperCase() + p.slice(1)}</button>
        ))}
      </div>
    </div>

    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            <th style={{ textAlign: 'left', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Agent</th>
            <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Conversations</th>
            <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Messages</th>
            <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Resolved</th>
            <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Avg Intent</th>
            <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>CSAT</th>
            <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>High Intent</th>
          </tr>
        </thead>
        <tbody>
          {performance.agents.map((a) => (
            <tr key={a.user_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px' }}>
                <div style={{ fontWeight: 500 }}>{a.display_name}</div>
                <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{a.role}</div>
              </td>
              <td style={{ textAlign: 'center', padding: '8px', fontWeight: 600 }}>{a.total_conversations}</td>
              <td style={{ textAlign: 'center', padding: '8px' }}>{a.total_messages}</td>
              <td style={{ textAlign: 'center', padding: '8px' }}>
                <span style={{ color: '#10b981', fontWeight: 600 }}>{a.resolved_conversations}</span>
              </td>
              <td style={{ textAlign: 'center', padding: '8px' }}>{a.avg_intent_score}</td>
              <td style={{ textAlign: 'center', padding: '8px' }}>
                {a.avg_csat > 0 ? (
                  <span style={{ color: a.avg_csat >= 4 ? '#10b981' : a.avg_csat >= 3 ? '#f59e0b' : '#ef4444', fontWeight: 600 }}>
                    {a.avg_csat} ⭐ ({a.csat_count})
                  </span>
                ) : '-'}
              </td>
              <td style={{ textAlign: 'center', padding: '8px' }}>
                <span style={{ color: '#3b82f6', fontWeight: 600 }}>{a.high_intent_count}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
)}
```

### Edit: `frontend/src/lib/i18n.js`

Add keys:

English:
```javascript
teams_title: "Teams",
teams_create: "+ Create Team",
teams_add_member: "+ Add member",
teams_members: "members",
perf_title: "Agent Performance",
perf_conversations: "Conversations",
perf_messages: "Messages",
perf_resolved: "Resolved",
perf_avg_intent: "Avg Intent",
perf_csat: "CSAT",
perf_high_intent: "High Intent",
```

Turkish:
```javascript
teams_title: "Ekipler",
teams_create: "+ Ekip Oluştur",
teams_add_member: "+ Üye ekle",
teams_members: "üye",
perf_title: "Agent Performansı",
perf_conversations: "Konuşmalar",
perf_messages: "Mesajlar",
perf_resolved: "Çözümlenen",
perf_avg_intent: "Ort. Niyet",
perf_csat: "CSAT",
perf_high_intent: "Yüksek Niyet",
```

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before teams"`
2. Apply. Delete .db if needed. Restart backend. Re-create persona + catalog.
3. Register admin, create 2 agent users.
4. Create a team "Sales" → add both agents as members.
5. Send Instagram DM → conversation auto-assigned to an agent in the team.
6. Open Team page → see Teams section with members → see Performance table.
7. Check agent performance metrics update as conversations come in.

## SUMMARY

NEW:
- backend/app/models/team.py
- backend/app/api/teams.py
- backend/app/api/agent_performance.py

EDITED:
- backend/app/models/__init__.py (1 import)
- backend/app/models/conversation_state.py (1 new column)
- backend/app/main.py (4 lines)
- backend/app/services/assignment.py (updated to support teams)
- frontend/src/pages/UsersPage.jsx (teams section + performance table)
- frontend/src/lib/i18n.js (new keys)

## DO NOT
- ❌ DO NOT rewrite any file
- ❌ DO NOT push to git
- ❌ DO NOT touch persona, catalog, voice, analytics pages

## START NOW. Checkpoint first.
