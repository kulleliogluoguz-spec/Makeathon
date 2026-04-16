# MASTER PROMPT: Analytics & Reporting Dashboard

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before analytics"` as safety checkpoint.
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog manager, Instagram/Messenger webhooks, livechat, or existing pages.

## WHAT THIS DOES

A new /analytics page with real-time performance metrics, charts, and breakdowns. Shows:

1. **Overview Cards** — total conversations, total customers, avg intent score, avg response (today / this week / this month)
2. **Channel Distribution** — pie chart showing Instagram vs Messenger vs LiveChat conversation counts
3. **Intent Score Distribution** — bar chart showing how many conversations are in each score range (0-20, 21-40, 41-60, 61-80, 81-100)
4. **Sales Funnel** — how many customers at each stage (awareness → interest → consideration → decision → purchase)
5. **Category Breakdown** — which categories are most common (bar chart)
6. **Daily Conversation Volume** — line chart showing conversations per day over last 30 days
7. **Top Products Mentioned** — which products come up most in conversations
8. **Time Period Filter** — today / this week / this month / all time

## BACKEND — NEW FILE

### New file: `backend/app/api/analytics.py`

```python
"""Analytics and reporting API."""

from datetime import datetime, timedelta
from collections import Counter
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.conversation_state import ConversationState
from app.models.customer import Customer

router = APIRouter()


def get_date_filter(period: str):
    """Return a datetime cutoff based on the period string."""
    now = datetime.utcnow()
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        return now - timedelta(days=7)
    elif period == "month":
        return now - timedelta(days=30)
    else:
        return None  # all time


@router.get("/analytics/overview")
async def get_overview(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Get overview metrics: total conversations, customers, avg score, etc."""
    cutoff = get_date_filter(period)

    # Conversations
    conv_query = select(ConversationState)
    if cutoff:
        conv_query = conv_query.where(ConversationState.last_message_at >= cutoff)
    conv_result = await db.execute(conv_query)
    conversations = conv_result.scalars().all()

    # Customers
    cust_query = select(Customer)
    if cutoff:
        cust_query = cust_query.where(Customer.created_at >= cutoff)
    cust_result = await db.execute(cust_query)
    customers = cust_result.scalars().all()

    # Calculations
    total_convs = len(conversations)
    total_customers = len(customers)
    total_messages = sum(c.message_count or 0 for c in conversations)
    avg_score = round(sum(c.intent_score or 0 for c in conversations) / max(total_convs, 1), 1)

    # High intent count (score >= 70)
    high_intent = sum(1 for c in conversations if (c.intent_score or 0) >= 70)

    # Active today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_today = sum(1 for c in conversations if c.last_message_at and c.last_message_at >= today_start)

    return {
        "total_conversations": total_convs,
        "total_customers": total_customers,
        "total_messages": total_messages,
        "avg_intent_score": avg_score,
        "high_intent_count": high_intent,
        "active_today": active_today,
        "period": period,
    }


@router.get("/analytics/channels")
async def get_channel_distribution(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Channel distribution — how many conversations per channel."""
    cutoff = get_date_filter(period)
    query = select(ConversationState)
    if cutoff:
        query = query.where(ConversationState.last_message_at >= cutoff)
    result = await db.execute(query)
    conversations = result.scalars().all()

    counter = Counter(c.channel or "unknown" for c in conversations)
    return {
        "channels": [
            {"name": k, "count": v}
            for k, v in counter.most_common()
        ]
    }


@router.get("/analytics/intent-distribution")
async def get_intent_distribution(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Intent score distribution in ranges."""
    cutoff = get_date_filter(period)
    query = select(ConversationState)
    if cutoff:
        query = query.where(ConversationState.last_message_at >= cutoff)
    result = await db.execute(query)
    conversations = result.scalars().all()

    ranges = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for c in conversations:
        score = c.intent_score or 0
        if score <= 20:
            ranges["0-20"] += 1
        elif score <= 40:
            ranges["21-40"] += 1
        elif score <= 60:
            ranges["41-60"] += 1
        elif score <= 80:
            ranges["61-80"] += 1
        else:
            ranges["81-100"] += 1

    return {"distribution": [{"range": k, "count": v} for k, v in ranges.items()]}


@router.get("/analytics/funnel")
async def get_sales_funnel(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Sales funnel — count per stage."""
    cutoff = get_date_filter(period)
    query = select(ConversationState)
    if cutoff:
        query = query.where(ConversationState.last_message_at >= cutoff)
    result = await db.execute(query)
    conversations = result.scalars().all()

    stage_order = ["awareness", "interest", "consideration", "decision", "purchase", "objection", "post_purchase"]
    counter = Counter(c.stage or "awareness" for c in conversations)

    return {
        "funnel": [
            {"stage": s, "count": counter.get(s, 0)}
            for s in stage_order
        ]
    }


@router.get("/analytics/categories")
async def get_category_breakdown(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Category tag frequency."""
    cutoff = get_date_filter(period)
    query = select(ConversationState)
    if cutoff:
        query = query.where(ConversationState.last_message_at >= cutoff)
    result = await db.execute(query)
    conversations = result.scalars().all()

    counter = Counter()
    for c in conversations:
        for cat in (c.categories or []):
            counter[cat] += 1

    return {"categories": [{"name": k, "count": v} for k, v in counter.most_common(10)]}


@router.get("/analytics/daily-volume")
async def get_daily_volume(days: int = Query(30), db: AsyncSession = Depends(get_db)):
    """Conversation count per day for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(ConversationState).where(ConversationState.created_at >= cutoff)
    )
    conversations = result.scalars().all()

    daily = Counter()
    for c in conversations:
        if c.created_at:
            day_str = c.created_at.strftime("%Y-%m-%d")
            daily[day_str] += 1

    # Fill missing days with 0
    all_days = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        all_days.append({"date": d, "count": daily.get(d, 0)})

    return {"daily": all_days}


@router.get("/analytics/top-products")
async def get_top_products(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    """Most mentioned products across conversations."""
    cutoff = get_date_filter(period)
    query = select(ConversationState)
    if cutoff:
        query = query.where(ConversationState.last_message_at >= cutoff)
    result = await db.execute(query)
    conversations = result.scalars().all()

    counter = Counter()
    for c in conversations:
        for pid in (c.products_mentioned or []):
            counter[pid] += 1

    # Resolve product names
    top_ids = [pid for pid, _ in counter.most_common(10)]
    products_map = {}
    if top_ids:
        try:
            from app.models.catalog_models import Product
            prod_result = await db.execute(select(Product).where(Product.id.in_(top_ids)))
            for p in prod_result.scalars().all():
                products_map[p.id] = p.name
        except Exception:
            pass

    return {
        "products": [
            {"id": pid, "name": products_map.get(pid, pid[:8] + "..."), "mentions": count}
            for pid, count in counter.most_common(10)
        ]
    }
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.analytics import router as analytics_router
```

Add include_router:
```python
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
```

## FRONTEND — NEW FILE

### New file: `frontend/src/pages/AnalyticsPage.jsx`

```jsx
import { useState, useEffect } from 'react';

const CHANNEL_COLORS = {
  instagram: '#e1306c',
  messenger: '#0084ff',
  livechat: '#10b981',
  unknown: '#94a3b8',
};

const CHANNEL_LABELS = {
  instagram: 'Instagram',
  messenger: 'Messenger',
  livechat: 'Live Chat',
};

const STAGE_COLORS = {
  awareness: '#94a3b8',
  interest: '#3b82f6',
  consideration: '#8b5cf6',
  decision: '#f59e0b',
  purchase: '#10b981',
  objection: '#ef4444',
  post_purchase: '#06b6d4',
};

function MetricCard({ label, value, sub }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
      padding: '1.25rem', flex: 1, minWidth: '150px',
    }}>
      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: '1.75rem', fontWeight: 600 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '2px' }}>{sub}</div>}
    </div>
  );
}

function BarChart({ data, colorFn, labelKey, valueKey, maxHeight }) {
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: maxHeight || '160px' }}>
      {data.map((d, i) => {
        const pct = ((d[valueKey] || 0) / max) * 100;
        const color = typeof colorFn === 'function' ? colorFn(d) : colorFn || '#3b82f6';
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '4px' }}>{d[valueKey]}</div>
            <div style={{
              width: '100%', maxWidth: '60px', background: color,
              borderRadius: '4px 4px 0 0', height: `${Math.max(pct, 3)}%`,
              transition: 'height 0.3s',
            }} />
            <div style={{ fontSize: '0.65rem', color: '#6b7280', marginTop: '6px', textAlign: 'center' }}>
              {d[labelKey]}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MiniLineChart({ data }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map(d => d.count), 1);
  const w = 100;
  const h = 40;
  const points = data.map((d, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * w;
    const y = h - (d.count / max) * h;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: '120px' }} preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke="#3b82f6"
        strokeWidth="1.5"
        points={points}
      />
      <polyline
        fill="url(#grad)"
        stroke="none"
        points={`0,${h} ${points} ${w},${h}`}
      />
      <defs>
        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('month');
  const [overview, setOverview] = useState(null);
  const [channels, setChannels] = useState([]);
  const [intentDist, setIntentDist] = useState([]);
  const [funnel, setFunnel] = useState([]);
  const [categories, setCategories] = useState([]);
  const [daily, setDaily] = useState([]);
  const [topProducts, setTopProducts] = useState([]);

  const load = async () => {
    const p = `period=${period}`;
    try {
      const [ov, ch, id, fn, ct, dl, tp] = await Promise.all([
        fetch(`/api/v1/analytics/overview?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/channels?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/intent-distribution?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/funnel?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/categories?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/daily-volume?days=30`).then(r => r.json()),
        fetch(`/api/v1/analytics/top-products?${p}`).then(r => r.json()),
      ]);
      setOverview(ov);
      setChannels(ch.channels || []);
      setIntentDist(id.distribution || []);
      setFunnel(fn.funnel || []);
      setCategories(ct.categories || []);
      setDaily(dl.daily || []);
      setTopProducts(tp.products || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, [period]);

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Analytics</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Performance overview across all channels</p>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          {[
            { value: 'today', label: 'Today' },
            { value: 'week', label: 'Week' },
            { value: 'month', label: 'Month' },
            { value: 'all', label: 'All Time' },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              style={{
                padding: '6px 14px', fontSize: '0.8rem', borderRadius: '9999px',
                background: period === opt.value ? '#000' : '#fff',
                color: period === opt.value ? '#fff' : '#374151',
                border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
              }}
            >{opt.label}</button>
          ))}
        </div>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <MetricCard label="Conversations" value={overview.total_conversations} />
          <MetricCard label="Customers" value={overview.total_customers} />
          <MetricCard label="Messages" value={overview.total_messages} />
          <MetricCard label="Avg Intent Score" value={overview.avg_intent_score} />
          <MetricCard label="High Intent (70+)" value={overview.high_intent_count} sub="Ready to buy" />
          <MetricCard label="Active Today" value={overview.active_today} />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Channel Distribution */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Channel Distribution</h3>
          {channels.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No data</div>
          ) : (
            <div>
              {channels.map((ch, i) => {
                const total = channels.reduce((s, c) => s + c.count, 0);
                const pct = total > 0 ? Math.round((ch.count / total) * 100) : 0;
                const color = CHANNEL_COLORS[ch.name] || '#94a3b8';
                return (
                  <div key={i} style={{ marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500 }}>{CHANNEL_LABELS[ch.name] || ch.name}</span>
                      <span style={{ color: '#6b7280' }}>{ch.count} ({pct}%)</span>
                    </div>
                    <div style={{ height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: '4px' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Intent Score Distribution */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Intent Score Distribution</h3>
          <BarChart
            data={intentDist}
            labelKey="range"
            valueKey="count"
            colorFn={(d) => {
              if (d.range === '81-100') return '#10b981';
              if (d.range === '61-80') return '#3b82f6';
              if (d.range === '41-60') return '#f59e0b';
              return '#94a3b8';
            }}
          />
        </div>

        {/* Sales Funnel */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Sales Funnel</h3>
          <BarChart
            data={funnel}
            labelKey="stage"
            valueKey="count"
            colorFn={(d) => STAGE_COLORS[d.stage] || '#94a3b8'}
          />
        </div>

        {/* Category Breakdown */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Categories</h3>
          {categories.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No data</div>
          ) : (
            categories.map((cat, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontSize: '0.85rem' }}>
                <span>{cat.name.replace(/_/g, ' ')}</span>
                <span style={{ fontWeight: 600 }}>{cat.count}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Daily Volume */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Daily Conversation Volume (Last 30 Days)</h3>
        <MiniLineChart data={daily} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#9ca3af', marginTop: '4px' }}>
          <span>{daily.length > 0 ? daily[0].date : ''}</span>
          <span>{daily.length > 0 ? daily[daily.length - 1].date : ''}</span>
        </div>
      </div>

      {/* Top Products */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Top Mentioned Products</h3>
        {topProducts.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No product mentions yet</div>
        ) : (
          topProducts.map((p, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
              <div>
                <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>{i + 1}. {p.name}</span>
              </div>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#3b82f6' }}>{p.mentions} mentions</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

### Edit: `frontend/src/App.jsx`

Add import:
```jsx
import AnalyticsPage from './pages/AnalyticsPage';
```

Add route:
```jsx
<Route path="/analytics" element={<AnalyticsPage />} />
```

Add nav link:
```jsx
<Link to="/analytics">Analytics</Link>
```

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before analytics"`
2. Apply changes. Restart backend.
3. Test endpoints:
```bash
curl "http://localhost:8000/api/v1/analytics/overview?period=all" | python3 -m json.tool
curl "http://localhost:8000/api/v1/analytics/channels?period=all" | python3 -m json.tool
curl "http://localhost:8000/api/v1/analytics/intent-distribution?period=all" | python3 -m json.tool
curl "http://localhost:8000/api/v1/analytics/funnel?period=all" | python3 -m json.tool
curl "http://localhost:8000/api/v1/analytics/daily-volume?days=30" | python3 -m json.tool
```
4. Open frontend → /analytics → see all charts and metrics.
5. Toggle between Today / Week / Month / All Time — data should update.
6. Send some Instagram DMs to create more data, then refresh analytics.

## SUMMARY

NEW:
- backend/app/api/analytics.py
- frontend/src/pages/AnalyticsPage.jsx

EDITED:
- backend/app/main.py (2 lines)
- frontend/src/App.jsx (1 import + 1 route + 1 link)

## DO NOT
- ❌ DO NOT rewrite any existing file
- ❌ DO NOT touch other pages or webhooks
- ❌ DO NOT push to git

## START NOW. Checkpoint first.
