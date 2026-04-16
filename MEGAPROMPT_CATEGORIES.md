# MASTER PROMPT: Category/Tag System + AI Auto-Tagging

## CRITICAL RULES

1. This is ADDITIVE. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before categories"` as safety checkpoint.
3. Do NOT push to git at any point.
4. Do NOT modify existing pages layouts. Only ADD a new page and minimal additions to existing pages.
5. Do NOT touch persona builder, voice builder, catalog manager.

## WHAT THIS FEATURE DOES

Each conversation gets 1-4 category tags automatically assigned by AI after every message. Categories come from two sources:

1. **Built-in categories** (always available, cannot be deleted):
   - order — customer is asking about an order or wants to place one
   - return — customer wants to return or exchange
   - complaint — customer is unhappy, complaining
   - sales_opportunity — clear buying interest, qualified lead
   - pricing_question — asking about prices, discounts, payment
   - shipping_question — asking about delivery, shipping, tracking
   - technical_support — product doesn't work, needs help using it
   - information_request — general questions about business, hours, location
   - urgency — customer needs immediate attention
   - greeting — just saying hello, no real intent yet

2. **Custom categories** (user-managed):
   - User can add, edit, delete custom categories
   - Each category has: name, description (helps AI decide when to use it), color
   - AI combines built-in + custom categories when tagging

After every Instagram message, AI looks at the conversation and returns 1-4 tags. Tags are saved to ConversationState.categories. Dashboard shows tags on each conversation. Filter conversations by tag.

## BACKEND — NEW FILES

### File 1: `backend/app/models/category.py` (NEW)

```python
"""Category/Tag model for conversation classification."""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=gen_uuid)
    slug = Column(String, unique=True, nullable=False, index=True)  # e.g. "vip_customer"
    name = Column(String, nullable=False)  # display label
    description = Column(Text, default="")  # helps AI decide when to apply
    color = Column(String, default="#64748b")  # hex color for UI
    is_builtin = Column(Boolean, default=False)  # built-in cannot be deleted
    sort_order = Column(String, default="0")  # for display ordering

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.category import Category  # noqa
```

### File 2: `backend/app/services/category_seeder.py` (NEW)

```python
"""Seeds built-in categories on startup if they don't exist."""

from sqlalchemy import select
from app.core.database import async_session
from app.models.category import Category


BUILTIN_CATEGORIES = [
    {"slug": "order", "name": "Order", "description": "Customer is asking about an order status, or wants to place an order.", "color": "#10b981"},
    {"slug": "return", "name": "Return", "description": "Customer wants to return, exchange, or refund a purchase.", "color": "#f59e0b"},
    {"slug": "complaint", "name": "Complaint", "description": "Customer is unhappy, complaining, expressing negative sentiment.", "color": "#ef4444"},
    {"slug": "sales_opportunity", "name": "Sales Opportunity", "description": "Clear buying interest, customer is qualified and close to purchase.", "color": "#8b5cf6"},
    {"slug": "pricing_question", "name": "Pricing Question", "description": "Customer is asking about prices, discounts, or payment methods.", "color": "#3b82f6"},
    {"slug": "shipping_question", "name": "Shipping Question", "description": "Customer is asking about delivery time, shipping cost, or tracking.", "color": "#06b6d4"},
    {"slug": "technical_support", "name": "Technical Support", "description": "Customer needs help using a product or service that is not working.", "color": "#ec4899"},
    {"slug": "information_request", "name": "Information", "description": "General questions about the business, hours, location, products.", "color": "#94a3b8"},
    {"slug": "urgency", "name": "Urgent", "description": "Customer needs immediate attention or shows signs of urgency.", "color": "#dc2626"},
    {"slug": "greeting", "name": "Greeting", "description": "Just saying hello, small talk, no specific intent yet.", "color": "#cbd5e1"},
]


async def seed_builtin_categories():
    """Insert built-in categories if they don't already exist."""
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
```

### File 3: `backend/app/services/category_tagger.py` (NEW)

```python
"""AI-powered category/tag assignment using gpt-4.1-nano."""

import os
import json
import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from app.core.database import async_session
from app.models.category import Category

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def get_all_categories() -> list:
    async with async_session() as session:
        result = await session.execute(select(Category))
        cats = result.scalars().all()
        return [
            {"slug": c.slug, "name": c.name, "description": c.description}
            for c in cats
        ]


async def auto_tag_conversation(messages: list) -> list:
    """Given a conversation, return a list of category slugs (1-4) that apply.
    Uses gpt-4.1-nano with the full list of available categories.
    """
    if not OPENAI_API_KEY or not messages:
        return []

    categories = await get_all_categories()
    if not categories:
        return []

    cat_list_text = "\n".join([
        f"- {c['slug']}: {c['name']} — {c['description']}"
        for c in categories
    ])
    valid_slugs = {c["slug"] for c in categories}

    recent = messages[-10:]
    transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])

    system_prompt = f"""You are a conversation classifier. Given a conversation, select 1-4 category tags that best describe the current state of the conversation.

Available categories:
{cat_list_text}

Rules:
- Return ONLY slugs from the list above. Do not invent new slugs.
- Return 1-4 tags maximum. If only one clearly applies, return just one.
- If no category fits well, return an empty list.
- Base your decision on the most recent messages — what is the customer currently asking or doing?

Return JSON: {{"tags": ["slug1", "slug2"]}}"""

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
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        tags = parsed.get("tags", [])

        # Validate — only return slugs that exist
        return [t for t in tags if t in valid_slugs][:4]
    except Exception as e:
        print(f"Category tagging error: {e}")
        return []
```

### File 4: `backend/app/api/categories.py` (NEW)

```python
"""Category management API."""

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.models.category import Category

router = APIRouter()


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", slug).strip("_")
    return slug


@router.get("/categories/")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.is_builtin.desc(), Category.name))
    cats = result.scalars().all()
    return [_serialize(c) for c in cats]


@router.post("/categories/")
async def create_category(body: dict, db: AsyncSession = Depends(get_db)):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    slug = slugify(body.get("slug") or name)
    # Check uniqueness
    result = await db.execute(select(Category).where(Category.slug == slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Slug already exists: {slug}")

    category = Category(
        slug=slug,
        name=name,
        description=body.get("description", ""),
        color=body.get("color", "#64748b"),
        is_builtin=False,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return _serialize(category)


@router.patch("/categories/{category_id}")
async def update_category(category_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # For built-in: only description and color are editable
    if category.is_builtin:
        for field in ("description", "color"):
            if field in body:
                setattr(category, field, body[field])
    else:
        for field in ("name", "description", "color"):
            if field in body:
                setattr(category, field, body[field])

    category.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(category)
    return _serialize(category)


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in categories")
    await db.delete(category)
    await db.commit()
    return {"status": "deleted"}


def _serialize(c: Category) -> dict:
    return {
        "id": c.id,
        "slug": c.slug,
        "name": c.name,
        "description": c.description or "",
        "color": c.color or "#64748b",
        "is_builtin": c.is_builtin,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
```

### Edit: `backend/app/main.py`

Add these imports near the other router imports:
```python
from app.api.categories import router as categories_router
from app.services.category_seeder import seed_builtin_categories
```

Add these lines near the other include_router calls:
```python
app.include_router(categories_router, prefix="/api/v1", tags=["Categories"])
```

Find the existing startup event (where `Base.metadata.create_all` is called). AFTER the tables are created, add a call to seed built-in categories:

```python
# After Base.metadata.create_all
await seed_builtin_categories()
```

If the startup function is something like `@app.on_event("startup")`, add this line at the end of that function. Do NOT change anything else in main.py.

### Edit: `backend/app/models/conversation_state.py`

Add ONE new column to the ConversationState model for storing assigned category slugs:

Find the existing column definitions and ADD this line (place it near other JSON columns):

```python
categories = Column(JSON, default=list)  # list of category slugs
```

Do NOT remove or modify any other column.

### Edit: `backend/app/api/instagram.py`

Integrate auto-tagging into the webhook flow.

1. Add this import at the top:
```python
from app.services.category_tagger import auto_tag_conversation
```

2. In the `update_conversation_state` function (or wherever conversation state is updated after the AI reply is generated), ADD this logic BEFORE the session commit:

```python
# Auto-tag the conversation
try:
    tags = await auto_tag_conversation(list(state.messages or []))
    if tags:
        state.categories = tags
except Exception as e:
    print(f"Auto-tagging error: {e}")
```

If the function signature or structure is different, just insert the tagging call at the right place — after messages are updated, before commit. The key is that `state.categories` gets assigned the result of `auto_tag_conversation`.

Do NOT remove or modify any other logic in instagram.py.

### Edit: `backend/app/api/conversations_api.py`

Update the serialization to include the `categories` field.

Find the `list_conversations` and `get_conversation` endpoints. In the dict returned for each conversation, ADD this field:

```python
"categories": s.categories or [],
```

(For `get_conversation`, use `state.categories or []`.)

Also, add support for filtering by tag in `list_conversations`. Update the function signature and query:

```python
from typing import Optional
from fastapi import Query

@router.get("/conversations/")
async def list_conversations(
    tag: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConversationState).order_by(desc(ConversationState.last_message_at))
    )
    states = result.scalars().all()

    # Post-query filter by tag (since categories is JSON)
    if tag:
        states = [s for s in states if tag in (s.categories or [])]

    return [...]  # keep existing serialization, but now also include "categories"
```

Do NOT rewrite the endpoints completely. Just add the filter logic and the new field in the response.

## FRONTEND — NEW FILES ONLY

### New file: `frontend/src/pages/CategoriesPage.jsx`

```jsx
import { useState, useEffect } from 'react';

const COLOR_PRESETS = [
  '#64748b', '#ef4444', '#f59e0b', '#10b981', '#3b82f6',
  '#8b5cf6', '#ec4899', '#06b6d4', '#dc2626', '#94a3b8',
];

export default function CategoriesPage() {
  const [categories, setCategories] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    try {
      const resp = await fetch('/api/v1/categories/');
      setCategories(await resp.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, []);

  const save = async (cat) => {
    if (cat.id) {
      await fetch(`/api/v1/categories/${cat.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cat),
      });
    } else {
      await fetch('/api/v1/categories/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cat),
      });
    }
    setShowCreate(false);
    setEditing(null);
    load();
  };

  const remove = async (id) => {
    if (!confirm('Delete this category?')) return;
    const resp = await fetch(`/api/v1/categories/${id}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json();
      alert(err.detail || 'Delete failed');
      return;
    }
    load();
  };

  const builtin = categories.filter(c => c.is_builtin);
  const custom = categories.filter(c => !c.is_builtin);

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Categories</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
            AI automatically tags conversations with these categories. Add custom ones for your use case.
          </p>
        </div>
        <button
          onClick={() => { setEditing({}); setShowCreate(true); }}
          style={{
            padding: '0.5rem 1rem', background: '#000', color: '#fff',
            borderRadius: '0.5rem', border: 'none', fontSize: '0.875rem', cursor: 'pointer',
          }}
        >+ Add Category</button>
      </div>

      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#6b7280', marginBottom: '0.75rem', textTransform: 'uppercase' }}>
          Built-in
        </h2>
        {builtin.map(c => (
          <CategoryRow key={c.id} cat={c} onEdit={() => { setEditing(c); setShowCreate(true); }} />
        ))}
      </section>

      <section>
        <h2 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#6b7280', marginBottom: '0.75rem', textTransform: 'uppercase' }}>
          Custom ({custom.length})
        </h2>
        {custom.length === 0 ? (
          <div style={{ color: '#9ca3af', padding: '1.5rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem' }}>
            No custom categories yet. Add ones specific to your business.
          </div>
        ) : (
          custom.map(c => (
            <CategoryRow
              key={c.id}
              cat={c}
              onEdit={() => { setEditing(c); setShowCreate(true); }}
              onDelete={() => remove(c.id)}
            />
          ))
        )}
      </section>

      {showCreate && (
        <CategoryModal
          initial={editing}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          onSave={save}
        />
      )}
    </div>
  );
}

function CategoryRow({ cat, onEdit, onDelete }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0.75rem 1rem', border: '1px solid #e5e7eb',
      borderRadius: '0.5rem', marginBottom: '0.5rem', background: '#fff',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: cat.color }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>
            {cat.name}
            {cat.is_builtin && (
              <span style={{ marginLeft: '8px', fontSize: '0.7rem', padding: '2px 6px', background: '#f3f4f6', color: '#6b7280', borderRadius: '4px' }}>
                built-in
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{cat.description}</div>
          <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '2px', fontFamily: 'monospace' }}>
            {cat.slug}
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button onClick={onEdit} style={{
          padding: '4px 12px', fontSize: '0.75rem', background: '#fff',
          border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
        }}>Edit</button>
        {onDelete && (
          <button onClick={onDelete} style={{
            padding: '4px 12px', fontSize: '0.75rem', background: '#fff',
            color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer',
          }}>Delete</button>
        )}
      </div>
    </div>
  );
}

function CategoryModal({ initial, onClose, onSave }) {
  const [data, setData] = useState({
    name: initial?.name || '',
    description: initial?.description || '',
    color: initial?.color || COLOR_PRESETS[0],
    ...(initial?.id ? { id: initial.id, is_builtin: initial.is_builtin } : {}),
  });

  const isEdit = !!initial?.id;
  const isBuiltin = !!initial?.is_builtin;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: '#fff', borderRadius: '0.75rem', padding: '1.5rem', width: '500px',
      }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
          {isEdit ? 'Edit Category' : 'New Category'}
        </h2>

        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>Name *</div>
          <input
            type="text"
            value={data.name}
            onChange={(e) => setData({ ...data, name: e.target.value })}
            disabled={isBuiltin}
            style={{
              width: '100%', padding: '6px 10px', fontSize: '0.875rem',
              border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none',
              background: isBuiltin ? '#f3f4f6' : '#fff',
            }}
          />
        </div>

        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>
            Description (helps AI decide when to apply)
          </div>
          <textarea
            value={data.description}
            onChange={(e) => setData({ ...data, description: e.target.value })}
            rows={3}
            placeholder="e.g., 'Customer is asking about wholesale or bulk pricing'"
            style={{
              width: '100%', padding: '6px 10px', fontSize: '0.875rem',
              border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', resize: 'vertical',
            }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>Color</div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {COLOR_PRESETS.map((c) => (
              <button
                key={c}
                onClick={() => setData({ ...data, color: c })}
                style={{
                  width: '28px', height: '28px', borderRadius: '50%',
                  background: c,
                  border: data.color === c ? '3px solid #000' : '1px solid #e5e7eb',
                  cursor: 'pointer',
                }}
              />
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
          <button onClick={onClose} style={{
            padding: '6px 16px', fontSize: '0.875rem', background: '#fff',
            border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
          }}>Cancel</button>
          <button
            onClick={() => onSave(data)}
            disabled={!data.name}
            style={{
              padding: '6px 16px', fontSize: '0.875rem', background: '#000', color: '#fff',
              border: 'none', borderRadius: '9999px', cursor: 'pointer',
              opacity: !data.name ? 0.4 : 1,
            }}
          >{isEdit ? 'Save' : 'Create'}</button>
        </div>
      </div>
    </div>
  );
}
```

### Edit: `frontend/src/pages/ConversationsPage.jsx`

Add category display and filtering to the existing Conversations page.

1. At the top, add:
```jsx
const [allCategories, setAllCategories] = useState([]);
const [activeTag, setActiveTag] = useState('');

useEffect(() => {
  fetch('/api/v1/categories/').then(r => r.json()).then(setAllCategories).catch(() => {});
}, []);
```

2. Modify the `loadConversations` function to include tag filter:
```jsx
const loadConversations = async () => {
  try {
    const params = activeTag ? `?tag=${activeTag}` : '';
    const resp = await fetch(`/api/v1/conversations/${params}`);
    const data = await resp.json();
    setConversations(data);
  } catch (e) { console.error(e); }
  setLoading(false);
};
```

3. Re-trigger loadConversations when activeTag changes. In the useEffect that loads conversations, add `activeTag` to dependencies.

4. Add a tag filter bar below the page title and above the list. Insert this JSX before the list area:

```jsx
{allCategories.length > 0 && (
  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '1rem' }}>
    <button
      onClick={() => setActiveTag('')}
      style={{
        fontSize: '0.75rem', padding: '4px 12px', borderRadius: '9999px',
        background: !activeTag ? '#000' : '#fff', color: !activeTag ? '#fff' : '#374151',
        border: '1px solid #e5e7eb', cursor: 'pointer',
      }}
    >All</button>
    {allCategories.map((c) => (
      <button
        key={c.id}
        onClick={() => setActiveTag(activeTag === c.slug ? '' : c.slug)}
        style={{
          fontSize: '0.75rem', padding: '4px 12px', borderRadius: '9999px',
          background: activeTag === c.slug ? c.color : '#fff',
          color: activeTag === c.slug ? '#fff' : '#374151',
          border: '1px solid #e5e7eb', cursor: 'pointer',
        }}
      >{c.name}</button>
    ))}
  </div>
)}
```

5. In the conversation card rendering, show the category badges. Find where conversation cards are rendered, and add this block inside each card (near the signals or below the stage badge):

```jsx
{c.categories && c.categories.length > 0 && (
  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
    {c.categories.map((slug) => {
      const cat = allCategories.find(x => x.slug === slug);
      if (!cat) return null;
      return (
        <span key={slug} style={{
          fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px',
          background: cat.color + '20', color: cat.color, fontWeight: 500,
        }}>{cat.name}</span>
      );
    })}
  </div>
)}
```

DO NOT restructure the ConversationsPage. Only ADD the filter bar and the category badge block.

### Edit: `frontend/src/App.jsx`

Add a new route for Categories. Make ONLY these minimal additions:

1. Add import:
```jsx
import CategoriesPage from './pages/CategoriesPage';
```

2. Add one Route:
```jsx
<Route path="/categories" element={<CategoriesPage />} />
```

3. Add one nav link in the navbar:
```jsx
<Link to="/categories">Categories</Link>
```

DO NOT change any other file.

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before categories"`

2. Apply all changes. Restart backend.

3. Verify built-in categories were seeded:
```bash
curl http://localhost:8000/api/v1/categories/ | python3 -m json.tool
# Should show 10 built-in categories
```

4. Frontend: navigate to `/categories`. See the 10 built-in categories. Try adding a custom one (e.g., "VIP Customer" with description "Frequent customer, high lifetime value").

5. Try editing a built-in (only description and color should be editable, name disabled).

6. Try deleting a built-in (should show error).

7. Delete the custom one you added (should succeed).

8. Send a DM to @big.m.ai from your test Instagram account. Try different messages:
   - "Hello" → should get tag `greeting`
   - "What's the price of the t-shirt?" → `pricing_question`, maybe `sales_opportunity`
   - "I want to return my order" → `return`, maybe `order`
   - "I love your shirts!" → `greeting` or `information_request`

9. Check that categories are now on the conversation:
```bash
curl http://localhost:8000/api/v1/conversations/ | python3 -m json.tool | grep -A2 categories
```

10. Open `/conversations` in the frontend → see the category badges on each conversation. Try clicking a tag filter → only conversations with that tag should show.

## SUMMARY

NEW:
- backend/app/models/category.py
- backend/app/services/category_seeder.py
- backend/app/services/category_tagger.py
- backend/app/api/categories.py
- frontend/src/pages/CategoriesPage.jsx

EDITED (minimal):
- backend/app/models/__init__.py (1 import line)
- backend/app/models/conversation_state.py (1 new column)
- backend/app/main.py (2 imports + 1 include_router + 1 seeder call in startup)
- backend/app/api/instagram.py (1 import + auto-tagging block in conversation state update)
- backend/app/api/conversations_api.py (categories field + tag filter)
- frontend/src/App.jsx (1 import + 1 route + 1 link)
- frontend/src/pages/ConversationsPage.jsx (filter bar + category badges)

## DO NOT

- ❌ DO NOT rewrite any existing file
- ❌ DO NOT modify persona builder, voice builder, catalog manager
- ❌ DO NOT change layout or styling of existing pages
- ❌ DO NOT push to git

## START NOW

Run checkpoint commit first, then create files in order, then apply edits, then test.
