# MASTER PROMPT: Customer CRM (Model + List Page + Manual Management)

## CRITICAL RULES

1. This is ADDITIVE. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before customer crm"` as safety checkpoint.
3. Do NOT push to git at any point.
4. Do NOT modify existing pages. Only ADD a new page.
5. Do NOT touch persona builder, voice builder, catalog manager, or conversations dashboard.

## WHAT THIS FEATURE DOES

Adds a Customer CRM layer to the system. Every person who interacts with the business (via Instagram DM today, later WhatsApp/LiveChat/etc.) has a Customer record with:
- Display name (auto-fetched from Instagram, editable)
- Handle / username
- Email, phone (optional, manual entry)
- Tags (array, e.g. "vip", "wholesale", "interested-in-tshirts")
- Custom fields (flexible JSON for anything extra)
- Notes (free text)
- Source channel (instagram / manual / future: whatsapp, etc.)
- External IDs (e.g. instagram_sender_id — links to their IG conversations)

Customers appear in a list page with search and filter. Clicking a customer opens a detail panel showing: profile info, all conversations, intent score timeline, all tags, notes.

Instagram webhook auto-creates/updates Customer records. User can also add/edit customers manually from the UI.

## BACKEND — NEW FILES

### File 1: `backend/app/models/customer.py` (NEW)

```python
"""Customer CRM model — unified identity across all channels."""

from sqlalchemy import Column, String, Text, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=gen_uuid)

    # Identity
    display_name = Column(String, default="")
    handle = Column(String, default="")  # @username on the source platform
    email = Column(String, default="")
    phone = Column(String, default="")
    avatar_url = Column(String, default="")

    # Classification
    tags = Column(JSON, default=list)  # ["vip", "wholesale", ...]
    custom_fields = Column(JSON, default=dict)  # {"company": "X", "source": "ads"}
    notes = Column(Text, default="")

    # Source & External IDs
    source = Column(String, default="manual")  # "instagram" | "manual" | "whatsapp" | "livechat"
    instagram_sender_id = Column(String, default="", index=True)
    whatsapp_phone = Column(String, default="", index=True)
    external_ids = Column(JSON, default=dict)  # flexible future-proof

    # Stats (updated by system)
    last_contact_at = Column(DateTime, nullable=True)
    total_messages = Column(String, default="0")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.customer import Customer  # noqa
```

### File 2: `backend/app/api/customers.py` (NEW)

```python
"""Customer CRM API."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc

from app.core.database import get_db
from app.models.customer import Customer

router = APIRouter()


@router.get("/customers/")
async def list_customers(
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List customers. Supports search by name/handle/email/phone, filter by tag, filter by source."""
    query = select(Customer)

    if search:
        term = f"%{search.lower()}%"
        query = query.where(
            or_(
                Customer.display_name.ilike(term),
                Customer.handle.ilike(term),
                Customer.email.ilike(term),
                Customer.phone.ilike(term),
            )
        )

    if source:
        query = query.where(Customer.source == source)

    query = query.order_by(desc(Customer.updated_at))
    result = await db.execute(query)
    customers = result.scalars().all()

    # Filter by tag (post-query, since tags are JSON)
    if tag:
        customers = [c for c in customers if tag in (c.tags or [])]

    return [_serialize(c) for c in customers]


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _serialize(customer)


@router.post("/customers/")
async def create_customer(body: dict, db: AsyncSession = Depends(get_db)):
    """Create a customer manually."""
    customer = Customer(
        display_name=body.get("display_name", ""),
        handle=body.get("handle", ""),
        email=body.get("email", ""),
        phone=body.get("phone", ""),
        avatar_url=body.get("avatar_url", ""),
        tags=body.get("tags", []),
        custom_fields=body.get("custom_fields", {}),
        notes=body.get("notes", ""),
        source=body.get("source", "manual"),
        instagram_sender_id=body.get("instagram_sender_id", ""),
        whatsapp_phone=body.get("whatsapp_phone", ""),
        external_ids=body.get("external_ids", {}),
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return _serialize(customer)


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    for field in (
        "display_name", "handle", "email", "phone", "avatar_url",
        "tags", "custom_fields", "notes", "source",
        "instagram_sender_id", "whatsapp_phone", "external_ids",
    ):
        if field in body:
            setattr(customer, field, body[field])

    customer.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(customer)
    return _serialize(customer)


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.delete(customer)
    await db.commit()
    return {"status": "deleted"}


@router.get("/customers/{customer_id}/conversations")
async def get_customer_conversations(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Get all conversations linked to this customer (by matching external IDs)."""
    from app.models.conversation_state import ConversationState

    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Find conversations matching any of the customer's external IDs
    conv_query = select(ConversationState)
    match_ids = []
    if customer.instagram_sender_id:
        match_ids.append(customer.instagram_sender_id)
    if customer.whatsapp_phone:
        match_ids.append(customer.whatsapp_phone)

    if not match_ids:
        return []

    conv_query = conv_query.where(ConversationState.sender_id.in_(match_ids))
    result = await db.execute(conv_query.order_by(desc(ConversationState.last_message_at)))
    conversations = result.scalars().all()

    return [
        {
            "id": c.id,
            "sender_id": c.sender_id,
            "channel": c.channel,
            "intent_score": c.intent_score,
            "stage": c.stage,
            "signals": c.signals or [],
            "message_count": c.message_count,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        }
        for c in conversations
    ]


def _serialize(c: Customer) -> dict:
    return {
        "id": c.id,
        "display_name": c.display_name,
        "handle": c.handle,
        "email": c.email,
        "phone": c.phone,
        "avatar_url": c.avatar_url,
        "tags": c.tags or [],
        "custom_fields": c.custom_fields or {},
        "notes": c.notes or "",
        "source": c.source,
        "instagram_sender_id": c.instagram_sender_id,
        "whatsapp_phone": c.whatsapp_phone,
        "external_ids": c.external_ids or {},
        "last_contact_at": c.last_contact_at.isoformat() if c.last_contact_at else None,
        "total_messages": c.total_messages,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
```

### Edit: `backend/app/main.py`

Add this import near the other router imports:
```python
from app.api.customers import router as customers_router
```

Add this line near the other include_router calls:
```python
app.include_router(customers_router, prefix="/api/v1", tags=["Customers"])
```

### Edit: `backend/app/api/instagram.py`

Integrate automatic Customer creation/update into the Instagram webhook flow.

At the top of the file, add this import:
```python
from app.models.customer import Customer
```

Add this new async helper function (place it near the other helpers):

```python
async def upsert_customer_from_instagram(sender_id: str, profile_name: str = None):
    """Create or update a Customer record for an Instagram sender.
    Returns the customer_id.
    """
    from app.core.database import async_session
    from sqlalchemy import select
    from datetime import datetime

    async with async_session() as session:
        result = await session.execute(
            select(Customer).where(Customer.instagram_sender_id == sender_id)
        )
        customer = result.scalar_one_or_none()

        if customer:
            # Update last contact
            customer.last_contact_at = datetime.utcnow()
            customer.updated_at = datetime.utcnow()
            # Update name if we have a better one
            if profile_name and not customer.display_name:
                customer.display_name = profile_name
            try:
                msgs = int(customer.total_messages or "0") + 1
            except (ValueError, TypeError):
                msgs = 1
            customer.total_messages = str(msgs)
            await session.commit()
            return customer.id

        # Create new customer
        customer = Customer(
            display_name=profile_name or "",
            handle="",
            source="instagram",
            instagram_sender_id=sender_id,
            tags=[],
            custom_fields={},
            notes="",
            external_ids={},
            last_contact_at=datetime.utcnow(),
            total_messages="1",
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)
        return customer.id
```

In the webhook POST handler (the function that processes incoming Instagram messages), find where the sender_id is extracted. Right after extracting sender_id and BEFORE generating the AI reply, add:

```python
# Extract profile name if available from the webhook payload
profile_name = None
try:
    # Instagram webhooks sometimes include sender profile info
    profile_name = event.get("sender", {}).get("username") or event.get("sender", {}).get("name")
except Exception:
    pass

# Create or update customer record
await upsert_customer_from_instagram(sender_id, profile_name)
```

If `event` is a different variable name in the existing code, match the correct variable that holds the messaging event. Do NOT rewrite the webhook handler — just insert these 2 blocks at the correct spot.

Do NOT remove or modify any other logic in instagram.py.

## FRONTEND — NEW FILES ONLY

### New file: `frontend/src/pages/CustomersPage.jsx`

```jsx
import { useState, useEffect } from 'react';

function Tag({ children, onRemove }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '0.75rem',
      padding: '3px 10px',
      background: '#e0e7ff',
      color: '#3730a3',
      borderRadius: '9999px',
      fontWeight: 500,
    }}>
      {children}
      {onRemove && (
        <button onClick={onRemove} style={{
          background: 'transparent', border: 'none', color: '#3730a3',
          cursor: 'pointer', padding: 0, fontSize: '0.875rem', lineHeight: 1,
        }}>×</button>
      )}
    </span>
  );
}

function SourceBadge({ source }) {
  const config = {
    instagram: { label: 'Instagram', color: '#e1306c' },
    whatsapp: { label: 'WhatsApp', color: '#25d366' },
    manual: { label: 'Manual', color: '#64748b' },
    livechat: { label: 'Live Chat', color: '#0ea5e9' },
  };
  const c = config[source] || { label: source, color: '#64748b' };
  return (
    <span style={{
      fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px',
      background: c.color + '20', color: c.color, fontWeight: 500,
    }}>{c.label}</span>
  );
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [conversations, setConversations] = useState([]);

  const load = async () => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (sourceFilter) params.append('source', sourceFilter);
    try {
      const resp = await fetch(`/api/v1/customers/?${params}`);
      setCustomers(await resp.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [search, sourceFilter]);

  const openCustomer = async (customer) => {
    setSelected(customer);
    try {
      const resp = await fetch(`/api/v1/customers/${customer.id}/conversations`);
      setConversations(await resp.json());
    } catch (e) { setConversations([]); }
  };

  const saveCustomer = async (customer) => {
    const resp = await fetch(`/api/v1/customers/${customer.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(customer),
    });
    const updated = await resp.json();
    setSelected(updated);
    load();
  };

  const deleteCustomer = async (id) => {
    if (!confirm('Delete this customer?')) return;
    await fetch(`/api/v1/customers/${id}`, { method: 'DELETE' });
    setSelected(null);
    load();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Customers</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Unified customer database across all channels</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            padding: '0.5rem 1rem', background: '#000', color: '#fff',
            borderRadius: '0.5rem', border: 'none', fontSize: '0.875rem', cursor: 'pointer',
          }}
        >+ Add Customer</button>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <input
          type="text"
          placeholder="Search by name, handle, email, phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1, padding: '0.5rem 1rem', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
          }}
        />
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          style={{
            padding: '0.5rem 1rem', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
          }}
        >
          <option value="">All sources</option>
          <option value="instagram">Instagram</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="manual">Manual</option>
          <option value="livechat">Live Chat</option>
        </select>
      </div>

      {customers.length === 0 ? (
        <div style={{
          color: '#9ca3af', padding: '3rem', textAlign: 'center',
          border: '1px dashed #e5e7eb', borderRadius: '0.75rem',
        }}>
          No customers yet. They will appear here when they message you, or you can add them manually.
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          {/* List */}
          <div style={{ flex: 1, maxWidth: '500px' }}>
            {customers.map((c) => (
              <div
                key={c.id}
                onClick={() => openCustomer(c)}
                style={{
                  padding: '1rem',
                  border: '1px solid',
                  borderColor: selected?.id === c.id ? '#000' : '#e5e7eb',
                  borderRadius: '0.75rem',
                  marginBottom: '0.5rem',
                  cursor: 'pointer',
                  background: '#fff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>
                    {c.display_name || c.handle || 'Unnamed'}
                  </div>
                  <SourceBadge source={c.source} />
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {c.handle && `@${c.handle} · `}
                  {c.email && `${c.email} · `}
                  {c.phone && `${c.phone} · `}
                  {c.total_messages} messages
                </div>
                {c.tags && c.tags.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {c.tags.map((t, i) => <Tag key={i}>{t}</Tag>)}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Detail */}
          <div style={{ flex: 1.2 }}>
            {!selected ? (
              <div style={{ color: '#9ca3af', padding: '2rem', textAlign: 'center' }}>
                Select a customer to view details
              </div>
            ) : (
              <CustomerDetail
                customer={selected}
                conversations={conversations}
                onSave={saveCustomer}
                onDelete={() => deleteCustomer(selected.id)}
              />
            )}
          </div>
        </div>
      )}

      {showCreate && (
        <CreateCustomerModal
          onClose={() => setShowCreate(false)}
          onCreate={async (data) => {
            const resp = await fetch('/api/v1/customers/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data),
            });
            const created = await resp.json();
            setShowCreate(false);
            load();
            openCustomer(created);
          }}
        />
      )}
    </div>
  );
}

function CustomerDetail({ customer, conversations, onSave, onDelete }) {
  const [editing, setEditing] = useState(null);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => { setEditing(customer); }, [customer]);

  if (!editing) return null;

  const update = (field, value) => setEditing({ ...editing, [field]: value });

  const addTag = () => {
    if (!tagInput.trim()) return;
    const newTags = [...(editing.tags || []), tagInput.trim()];
    setEditing({ ...editing, tags: newTags });
    setTagInput('');
  };

  const removeTag = (i) => {
    const newTags = (editing.tags || []).filter((_, idx) => idx !== i);
    setEditing({ ...editing, tags: newTags });
  };

  const hasChanges = JSON.stringify(editing) !== JSON.stringify(customer);

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#fff', padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Customer Details</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {hasChanges && (
            <button onClick={() => onSave(editing)} style={{
              padding: '4px 12px', fontSize: '0.75rem', background: '#000',
              color: '#fff', borderRadius: '9999px', border: 'none', cursor: 'pointer',
            }}>Save</button>
          )}
          <button onClick={onDelete} style={{
            padding: '4px 12px', fontSize: '0.75rem', background: '#fff',
            color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer',
          }}>Delete</button>
        </div>
      </div>

      <Field label="Display name" value={editing.display_name} onChange={(v) => update('display_name', v)} />
      <Field label="Handle / Username" value={editing.handle} onChange={(v) => update('handle', v)} prefix="@" />
      <Field label="Email" value={editing.email} onChange={(v) => update('email', v)} />
      <Field label="Phone" value={editing.phone} onChange={(v) => update('phone', v)} />

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>TAGS</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '6px' }}>
          {(editing.tags || []).map((t, i) => <Tag key={i} onRemove={() => removeTag(i)}>{t}</Tag>)}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            type="text"
            placeholder="Add tag..."
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') addTag(); }}
            style={{
              flex: 1, padding: '4px 10px', fontSize: '0.75rem',
              border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
            }}
          />
        </div>
      </div>

      <Field label="Notes" value={editing.notes} onChange={(v) => update('notes', v)} textarea />

      {(editing.instagram_sender_id || editing.whatsapp_phone) && (
        <div style={{ marginBottom: '1rem', fontSize: '0.75rem', color: '#6b7280' }}>
          {editing.instagram_sender_id && <div>IG Sender ID: {editing.instagram_sender_id}</div>}
          {editing.whatsapp_phone && <div>WhatsApp: {editing.whatsapp_phone}</div>}
          <div>Source: {editing.source}</div>
        </div>
      )}

      {conversations.length > 0 && (
        <div style={{ marginTop: '1.5rem', borderTop: '1px solid #e5e7eb', paddingTop: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>
            CONVERSATIONS ({conversations.length})
          </div>
          {conversations.map((c) => (
            <div key={c.id} style={{
              padding: '0.5rem 0.75rem', border: '1px solid #e5e7eb',
              borderRadius: '0.5rem', marginBottom: '0.5rem', fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{c.channel} · {c.message_count} messages</span>
                <span style={{ fontWeight: 500 }}>Score: {c.intent_score}</span>
              </div>
              <div style={{ color: '#6b7280', fontSize: '0.7rem', marginTop: '2px' }}>
                Stage: {c.stage} · Last: {c.last_message_at ? new Date(c.last_message_at).toLocaleString() : 'never'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange, prefix, textarea }) {
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>
        {label}
      </div>
      {textarea ? (
        <textarea
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          style={{
            width: '100%', padding: '6px 10px', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', resize: 'vertical',
          }}
        />
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {prefix && <span style={{ color: '#9ca3af' }}>{prefix}</span>}
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            style={{
              flex: 1, padding: '6px 10px', fontSize: '0.875rem',
              border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none',
            }}
          />
        </div>
      )}
    </div>
  );
}

function CreateCustomerModal({ onClose, onCreate }) {
  const [data, setData] = useState({
    display_name: '',
    handle: '',
    email: '',
    phone: '',
    source: 'manual',
    instagram_sender_id: '',
    whatsapp_phone: '',
    notes: '',
    tags: [],
  });

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: '#fff', borderRadius: '0.75rem', padding: '1.5rem',
        width: '500px', maxHeight: '90vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>Add Customer</h2>

        <Field label="Display name *" value={data.display_name} onChange={(v) => setData({ ...data, display_name: v })} />
        <Field label="Handle / Username" value={data.handle} onChange={(v) => setData({ ...data, handle: v })} prefix="@" />
        <Field label="Email" value={data.email} onChange={(v) => setData({ ...data, email: v })} />
        <Field label="Phone" value={data.phone} onChange={(v) => setData({ ...data, phone: v })} />

        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>Source</div>
          <select
            value={data.source}
            onChange={(e) => setData({ ...data, source: e.target.value })}
            style={{
              width: '100%', padding: '6px 10px', fontSize: '0.875rem',
              border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none',
            }}
          >
            <option value="manual">Manual</option>
            <option value="instagram">Instagram</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="livechat">Live Chat</option>
          </select>
        </div>

        {data.source === 'instagram' && (
          <Field label="Instagram Sender ID" value={data.instagram_sender_id} onChange={(v) => setData({ ...data, instagram_sender_id: v })} />
        )}
        {data.source === 'whatsapp' && (
          <Field label="WhatsApp Phone" value={data.whatsapp_phone} onChange={(v) => setData({ ...data, whatsapp_phone: v })} />
        )}

        <Field label="Notes" value={data.notes} onChange={(v) => setData({ ...data, notes: v })} textarea />

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.5rem' }}>
          <button onClick={onClose} style={{
            padding: '6px 16px', fontSize: '0.875rem', background: '#fff',
            border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
          }}>Cancel</button>
          <button
            onClick={() => onCreate(data)}
            disabled={!data.display_name && !data.handle}
            style={{
              padding: '6px 16px', fontSize: '0.875rem', background: '#000', color: '#fff',
              border: 'none', borderRadius: '9999px', cursor: 'pointer',
              opacity: (!data.display_name && !data.handle) ? 0.4 : 1,
            }}
          >Create</button>
        </div>
      </div>
    </div>
  );
}
```

### Edit: `frontend/src/App.jsx`

Make ONLY these minimal additions:

1. Add import at the top with other imports:
```jsx
import CustomersPage from './pages/CustomersPage';
```

2. Find the routes section. Add ONE new Route:
```jsx
<Route path="/customers" element={<CustomersPage />} />
```

3. Find the navbar. Add ONE new link next to existing ones (match the style of existing navbar links):
```jsx
<Link to="/customers">Customers</Link>
```

DO NOT restructure the navbar. DO NOT change any other file.

## TEST PLAN

1. Commit checkpoint FIRST:
```bash
git add -A && git commit -m "checkpoint before customer crm"
```

2. Apply all changes. Restart backend:
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

3. Verify endpoint works:
```bash
curl http://localhost:8000/api/v1/customers/
# Should return: []
```

4. Open frontend → navigate to /customers. See empty state with "Add Customer" button.

5. Test manual creation:
- Click "Add Customer"
- Fill in display name and handle, click Create
- Should appear in list
- Click on it → detail panel appears
- Edit name, add a tag, add notes
- Click Save
- Refresh page → changes persist

6. Test Instagram auto-creation:
- Send a DM to @big.m.ai from a test account
- Check `/api/v1/customers/?source=instagram` — new customer should be there automatically
- Open it in the frontend → should show Instagram source badge and sender ID
- Conversations section should show the active conversation

7. Test search and filter:
- Search by name → should filter
- Filter by source=instagram → should show only IG customers

## SUMMARY

NEW:
- backend/app/models/customer.py
- backend/app/api/customers.py
- frontend/src/pages/CustomersPage.jsx

EDITED (minimal):
- backend/app/models/__init__.py (1 import line)
- backend/app/main.py (2 lines)
- backend/app/api/instagram.py (imports + helper function + webhook integration)
- frontend/src/App.jsx (1 import + 1 route + 1 link)

## DO NOT

- ❌ DO NOT rewrite any existing file
- ❌ DO NOT modify existing pages, layouts, or styling
- ❌ DO NOT touch voice builder, voice picker, persona form, catalog manager, or conversations page
- ❌ DO NOT push to git

## START NOW

Run the checkpoint commit first, then create files in order, then test.
