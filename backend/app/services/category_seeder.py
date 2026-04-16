"""Seeds built-in categories on startup if they don't exist."""

from sqlalchemy import select
from app.core.database import async_session
from app.models.category import Category


BUILTIN_CATEGORIES = [
    {
        "slug": "high_sales_potential",
        "name": "Yüksek Satış Potansiyeli",
        "description": "Customer has very strong buying signals: asking about price, shipping, availability, ready to commit, showing urgency or clear intent to purchase soon. Intent score typically 70+.",
        "color": "#10b981",
    },
    {
        "slug": "sales_potential",
        "name": "Satış Potansiyeli Var",
        "description": "Customer is interested in products, asking follow-up questions, exploring options, showing moderate buying interest. Intent score typically 35-70.",
        "color": "#3b82f6",
    },
    {
        "slug": "no_sales_potential",
        "name": "Satış Potansiyeli Yok",
        "description": "Customer is just browsing, saying hello, asking general information, or has explicitly stated they don't want to buy. Intent score typically under 35.",
        "color": "#94a3b8",
    },
]


async def cleanup_old_builtin_categories():
    """Remove built-in categories that are no longer in the current list."""
    current_slugs = {c["slug"] for c in BUILTIN_CATEGORIES}
    async with async_session() as session:
        result = await session.execute(select(Category).where(Category.is_builtin == True))
        old_cats = result.scalars().all()
        for cat in old_cats:
            if cat.slug not in current_slugs:
                await session.delete(cat)
        await session.commit()


async def seed_builtin_categories():
    """Insert built-in categories if they don't already exist."""
    await cleanup_old_builtin_categories()
    async with async_session() as session:
        for cat_data in BUILTIN_CATEGORIES:
            result = await session.execute(select(Category).where(Category.slug == cat_data["slug"]))
            existing = result.scalar_one_or_none()
            if not existing:
                category = Category(
                    slug=cat_data["slug"],
                    name=cat_data["name"],
                    description=cat_data["description"],
                    color=cat_data["color"],
                    is_builtin=True,
                )
                session.add(category)
        await session.commit()
