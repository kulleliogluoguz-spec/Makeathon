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
