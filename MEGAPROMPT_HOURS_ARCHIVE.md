# MASTER PROMPT: Business Hours + Archive System

## CRITICAL RULES

1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before hours and archive"` as safety checkpoint.
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog manager.

## FEATURE 1 — BUSINESS HOURS

### Backend: `backend/app/models/business_settings.py` (NEW)

```python
"""Business settings — working hours, holidays, auto-reply messages."""

from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class BusinessSettings(Base):
    __tablename__ = "business_settings"

    id = Column(String, primary_key=True, default=gen_uuid)
    
    # Working hours: {"mon": {"start": "09:00", "end": "18:00", "enabled": true}, "tue": {...}, ...}
    working_hours = Column(JSON, default=dict)
    
    # Timezone (IANA format)
    timezone = Column(String, default="Europe/Berlin")
    
    # Auto-reply when outside business hours
    outside_hours_message = Column(Text, default="Şu anda mesai saatleri dışındayız. En kısa sürede size dönüş yapacağız. Mesai saatlerimiz: Pazartesi-Cuma 09:00-18:00")
    outside_hours_enabled = Column(Boolean, default=True)
    
    # Holiday dates: ["2026-01-01", "2026-04-23", ...]
    holidays = Column(JSON, default=list)
    holiday_message = Column(Text, default="Bugün tatil nedeniyle kapalıyız. İlk iş günü size dönüş yapacağız.")
    
    # Auto-archive inactive conversations after N hours (0 = disabled)
    auto_archive_hours = Column(String, default="48")
    
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Register in `app/models/__init__.py`:
```python
from app.models.business_settings import BusinessSettings  # noqa
```

### Backend: `backend/app/services/business_hours.py` (NEW)

```python
"""Check if current time is within business hours."""

from datetime import datetime, date
import pytz
from sqlalchemy import select

from app.core.database import async_session
from app.models.business_settings import BusinessSettings


DEFAULT_HOURS = {
    "mon": {"start": "09:00", "end": "18:00", "enabled": True},
    "tue": {"start": "09:00", "end": "18:00", "enabled": True},
    "wed": {"start": "09:00", "end": "18:00", "enabled": True},
    "thu": {"start": "09:00", "end": "18:00", "enabled": True},
    "fri": {"start": "09:00", "end": "18:00", "enabled": True},
    "sat": {"start": "00:00", "end": "00:00", "enabled": False},
    "sun": {"start": "00:00", "end": "00:00", "enabled": False},
}

DAY_MAP = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}


async def get_settings() -> dict:
    """Load business settings from DB. Returns dict with all fields."""
    async with async_session() as session:
        result = await session.execute(select(BusinessSettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            return {
                "working_hours": DEFAULT_HOURS,
                "timezone": "Europe/Berlin",
                "outside_hours_message": "Şu anda mesai saatleri dışındayız. En kısa sürede size dönüş yapacağız.",
                "outside_hours_enabled": True,
                "holidays": [],
                "holiday_message": "Bugün tatil nedeniyle kapalıyız.",
                "auto_archive_hours": "48",
            }
        return {
            "working_hours": settings.working_hours or DEFAULT_HOURS,
            "timezone": settings.timezone or "Europe/Berlin",
            "outside_hours_message": settings.outside_hours_message or "",
            "outside_hours_enabled": settings.outside_hours_enabled if settings.outside_hours_enabled is not None else True,
            "holidays": settings.holidays or [],
            "holiday_message": settings.holiday_message or "",
            "auto_archive_hours": settings.auto_archive_hours or "48",
        }


async def is_within_business_hours() -> tuple:
    """Returns (is_open: bool, message_if_closed: str)"""
    settings = await get_settings()
    
    if not settings["outside_hours_enabled"]:
        return True, ""
    
    try:
        tz = pytz.timezone(settings["timezone"])
    except Exception:
        tz = pytz.timezone("Europe/Berlin")
    
    now = datetime.now(tz)
    today_str = now.strftime("%Y-%m-%d")
    
    # Check holidays
    if today_str in settings["holidays"]:
        return False, settings["holiday_message"]
    
    # Check working hours for today
    day_key = DAY_MAP.get(now.weekday(), "mon")
    hours = settings["working_hours"].get(day_key, {})
    
    if not hours.get("enabled", False):
        return False, settings["outside_hours_message"]
    
    start_str = hours.get("start", "09:00")
    end_str = hours.get("end", "18:00")
    
    try:
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        if start_minutes <= current_minutes <= end_minutes:
            return True, ""
        else:
            return False, settings["outside_hours_message"]
    except Exception:
        return True, ""
```

### Backend: `backend/app/api/settings.py` (NEW)

```python
"""Business settings API."""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.business_settings import BusinessSettings

router = APIRouter()


@router.get("/settings/business-hours")
async def get_business_hours(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BusinessSettings).limit(1))
    s = result.scalar_one_or_none()
    if not s:
        from app.services.business_hours import DEFAULT_HOURS
        return {
            "working_hours": DEFAULT_HOURS,
            "timezone": "Europe/Berlin",
            "outside_hours_message": "Şu anda mesai saatleri dışındayız. En kısa sürede size dönüş yapacağız.",
            "outside_hours_enabled": True,
            "holidays": [],
            "holiday_message": "Bugün tatil nedeniyle kapalıyız.",
            "auto_archive_hours": "48",
        }
    return {
        "working_hours": s.working_hours or {},
        "timezone": s.timezone,
        "outside_hours_message": s.outside_hours_message,
        "outside_hours_enabled": s.outside_hours_enabled,
        "holidays": s.holidays or [],
        "holiday_message": s.holiday_message,
        "auto_archive_hours": s.auto_archive_hours,
    }


@router.put("/settings/business-hours")
async def update_business_hours(body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BusinessSettings).limit(1))
    s = result.scalar_one_or_none()
    if not s:
        s = BusinessSettings()
        db.add(s)
    
    for field in ("working_hours", "timezone", "outside_hours_message",
                  "outside_hours_enabled", "holidays", "holiday_message", "auto_archive_hours"):
        if field in body:
            setattr(s, field, body[field])
    
    s.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(s)
    return {"status": "saved"}
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.settings import router as settings_router
```

Add include_router:
```python
app.include_router(settings_router, prefix="/api/v1", tags=["Settings"])
```

### Edit: `backend/app/api/instagram.py`

Integrate business hours check. At the top, add:
```python
from app.services.business_hours import is_within_business_hours
```

In the webhook POST handler, AFTER extracting the message text and BEFORE generating the AI reply, add:

```python
# Check business hours
is_open, closed_message = await is_within_business_hours()
if not is_open and closed_message:
    await send_reply(sender_id, closed_message)
    # Still save the message to conversation state for when we're back
    await upsert_customer_from_instagram(sender_id)
    return {"status": "ok"}
```

This means: if outside hours, send the auto-reply and stop. Do NOT call the LLM. But still save the customer record.

Do NOT change any other logic in instagram.py.

### Add pytz to requirements.txt:
```
pytz==2024.1
```

## FEATURE 2 — ARCHIVE SYSTEM (in Customers page)

### Edit: `backend/app/models/customer.py`

Add ONE new column to the Customer model:
```python
is_archived = Column(Boolean, default=False, index=True)
```

Add this import at the top if not present:
```python
from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
```

### Edit: `backend/app/api/customers.py`

1. Add `is_archived` filter to list_customers. Add a new query parameter:
```python
archived: Optional[str] = Query(None),  # "true", "false", or None for all
```

After building the base query, add:
```python
if archived == "true":
    query = query.where(Customer.is_archived == True)
elif archived == "false" or archived is None:
    # Default: show only active (not archived) customers
    query = query.where(Customer.is_archived == False)
# If archived == "all", don't filter
```

Wait — we want 3 options: Active (default), Archived, All. So:
```python
if archived == "true":
    query = query.where(Customer.is_archived == True)
elif archived == "all":
    pass  # no filter, show everything
else:
    # Default: active only
    query = query.where(Customer.is_archived == False)
```

2. Add `is_archived` to the _serialize function output:
```python
"is_archived": c.is_archived or False,
```

3. Add archive/unarchive endpoint:
```python
@router.post("/customers/{customer_id}/archive")
async def archive_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404)
    customer.is_archived = True
    customer.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "archived"}


@router.post("/customers/{customer_id}/unarchive")
async def unarchive_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404)
    customer.is_archived = False
    customer.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "unarchived"}
```

4. In the instagram.py `upsert_customer_from_instagram` function, when a customer who is archived sends a NEW message, automatically unarchive them. Find the section where an existing customer is updated, and add:
```python
if customer.is_archived:
    customer.is_archived = False
```

### Edit: `frontend/src/pages/CustomersPage.jsx`

Add an Active/Archived/All toggle and archive buttons.

1. Add state:
```jsx
const [archiveFilter, setArchiveFilter] = useState('false');  // "false" = active, "true" = archived, "all" = all
```

2. Update the load function to include the archive filter:
```jsx
if (archiveFilter !== 'all') params.append('archived', archiveFilter);
else params.append('archived', 'all');
```

Add `archiveFilter` to the useEffect dependencies.

3. Add an Active/Archived/All toggle bar. Insert ABOVE the 4-column filter bar:

```jsx
<div style={{ display: 'flex', gap: '4px', marginBottom: '1rem' }}>
  {[
    { value: 'false', label: 'Active' },
    { value: 'true', label: 'Archived' },
    { value: 'all', label: 'All' },
  ].map((opt) => (
    <button
      key={opt.value}
      onClick={() => setArchiveFilter(opt.value)}
      style={{
        padding: '6px 16px', fontSize: '0.875rem', borderRadius: '9999px',
        background: archiveFilter === opt.value ? '#000' : '#fff',
        color: archiveFilter === opt.value ? '#fff' : '#374151',
        border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
      }}
    >{opt.label}</button>
  ))}
</div>
```

4. In the CustomerDetail component, add an Archive/Unarchive button next to the Delete button:

```jsx
<button
  onClick={async () => {
    const action = customer.is_archived ? 'unarchive' : 'archive';
    await fetch(`/api/v1/customers/${customer.id}/${action}`, { method: 'POST' });
    onSave({ ...customer, is_archived: !customer.is_archived });
  }}
  style={{
    padding: '4px 12px', fontSize: '0.75rem',
    background: customer.is_archived ? '#10b981' : '#f59e0b',
    color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer',
  }}
>
  {customer.is_archived ? 'Unarchive' : 'Archive'}
</button>
```

Find the existing buttons area (where Delete button is) and INSERT this button next to it. Do NOT restructure the buttons.

5. In the customer list card, show a subtle "Archived" indicator if the customer is archived:

After the source badge, add:
```jsx
{c.is_archived && (
  <span style={{
    fontSize: '0.7rem', padding: '2px 6px', background: '#fef3c7',
    color: '#92400e', borderRadius: '4px', marginLeft: '4px',
  }}>Archived</span>
)}
```

## FRONTEND — BUSINESS HOURS SETTINGS

Add a Settings section accessible from the navbar. This is a simple page to configure working hours.

### New file: `frontend/src/pages/SettingsPage.jsx`

```jsx
import { useState, useEffect } from 'react';

const DAYS = [
  { key: 'mon', label: 'Monday' },
  { key: 'tue', label: 'Tuesday' },
  { key: 'wed', label: 'Wednesday' },
  { key: 'thu', label: 'Thursday' },
  { key: 'fri', label: 'Friday' },
  { key: 'sat', label: 'Saturday' },
  { key: 'sun', label: 'Sunday' },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [holidayInput, setHolidayInput] = useState('');

  useEffect(() => {
    fetch('/api/v1/settings/business-hours')
      .then(r => r.json())
      .then(setSettings)
      .catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    await fetch('/api/v1/settings/business-hours', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateDay = (day, field, value) => {
    setSettings(prev => ({
      ...prev,
      working_hours: {
        ...prev.working_hours,
        [day]: { ...prev.working_hours[day], [field]: value },
      },
    }));
  };

  const addHoliday = () => {
    if (!holidayInput) return;
    setSettings(prev => ({
      ...prev,
      holidays: [...(prev.holidays || []), holidayInput],
    }));
    setHolidayInput('');
  };

  const removeHoliday = (i) => {
    setSettings(prev => ({
      ...prev,
      holidays: (prev.holidays || []).filter((_, idx) => idx !== i),
    }));
  };

  if (!settings) return <div style={{ padding: '2rem' }}>Loading...</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Settings</h1>
      <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' }}>
        Business hours, auto-reply, and archive settings
      </p>

      {/* Working Hours */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>Working Hours</h2>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>TIMEZONE</label>
          <select
            value={settings.timezone}
            onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
            style={{ padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }}
          >
            <option value="Europe/Berlin">Europe/Berlin (CET)</option>
            <option value="Europe/Istanbul">Europe/Istanbul (TRT)</option>
            <option value="Europe/London">Europe/London (GMT)</option>
            <option value="America/New_York">America/New York (EST)</option>
            <option value="UTC">UTC</option>
          </select>
        </div>

        {DAYS.map(({ key, label }) => {
          const day = settings.working_hours?.[key] || { start: '09:00', end: '18:00', enabled: false };
          return (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <label style={{ width: '100px', fontSize: '0.875rem', fontWeight: 500 }}>{label}</label>
              <input
                type="checkbox"
                checked={day.enabled || false}
                onChange={(e) => updateDay(key, 'enabled', e.target.checked)}
              />
              <input
                type="time"
                value={day.start || '09:00'}
                onChange={(e) => updateDay(key, 'start', e.target.value)}
                disabled={!day.enabled}
                style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '0.375rem', fontSize: '0.875rem', opacity: day.enabled ? 1 : 0.4 }}
              />
              <span style={{ color: '#6b7280' }}>to</span>
              <input
                type="time"
                value={day.end || '18:00'}
                onChange={(e) => updateDay(key, 'end', e.target.value)}
                disabled={!day.enabled}
                style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '0.375rem', fontSize: '0.875rem', opacity: day.enabled ? 1 : 0.4 }}
              />
            </div>
          );
        })}
      </section>

      {/* Outside Hours Message */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Outside Hours Auto-Reply</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem' }}>
            <input
              type="checkbox"
              checked={settings.outside_hours_enabled}
              onChange={(e) => setSettings({ ...settings, outside_hours_enabled: e.target.checked })}
            />
            Enabled
          </label>
        </div>
        <textarea
          value={settings.outside_hours_message}
          onChange={(e) => setSettings({ ...settings, outside_hours_message: e.target.value })}
          rows={3}
          style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', resize: 'vertical' }}
        />
      </section>

      {/* Holidays */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }}>Holidays</h2>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '0.75rem' }}>
          <input
            type="date"
            value={holidayInput}
            onChange={(e) => setHolidayInput(e.target.value)}
            style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}
          />
          <button onClick={addHoliday} style={{ padding: '6px 12px', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}>Add</button>
        </div>
        <textarea
          value={settings.holiday_message}
          onChange={(e) => setSettings({ ...settings, holiday_message: e.target.value })}
          rows={2}
          placeholder="Holiday auto-reply message"
          style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', marginBottom: '0.5rem', resize: 'vertical' }}
        />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {(settings.holidays || []).map((h, i) => (
            <span key={i} style={{ fontSize: '0.75rem', padding: '4px 10px', background: '#fef3c7', color: '#92400e', borderRadius: '9999px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              {h}
              <button onClick={() => removeHoliday(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontSize: '0.875rem' }}>×</button>
            </span>
          ))}
        </div>
      </section>

      {/* Auto-Archive */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }}>Auto-Archive</h2>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.75rem' }}>
          Automatically archive customers with no activity after this many hours. Set 0 to disable.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="number"
            value={settings.auto_archive_hours}
            onChange={(e) => setSettings({ ...settings, auto_archive_hours: e.target.value })}
            min="0"
            style={{ width: '80px', padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}
          />
          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>hours of inactivity</span>
        </div>
      </section>

      {/* Save */}
      <button
        onClick={save}
        disabled={saving}
        style={{
          padding: '0.75rem 2rem', background: '#000', color: '#fff',
          border: 'none', borderRadius: '0.5rem', fontSize: '1rem',
          cursor: saving ? 'wait' : 'pointer', opacity: saving ? 0.5 : 1,
        }}
      >
        {saving ? 'Saving...' : saved ? '✓ Saved!' : 'Save Settings'}
      </button>
    </div>
  );
}
```

### Edit: `frontend/src/App.jsx`

Add:
```jsx
import SettingsPage from './pages/SettingsPage';
```

Add route:
```jsx
<Route path="/settings" element={<SettingsPage />} />
```

Add nav link (use a gear icon or just text):
```jsx
<Link to="/settings">Settings</Link>
```

## DELETE OLD DATABASE

Because we added new columns (is_archived to Customer, new BusinessSettings table), the SQLite file needs to be regenerated. After applying all changes:

```bash
rm backend/*.db
```

Then restart backend. Tables will be recreated. You will need to re-upload your catalog and re-create your persona.

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before hours and archive"`
2. Apply all changes. Delete database: `rm backend/*.db`. Restart backend.
3. Open /settings. Configure working hours (enable Mon-Fri 09:00-18:00, disable Sat-Sun). Save.
4. Test outside hours: temporarily set today's end time to a time in the past (e.g. 00:01). Send an Instagram DM. Should get the "outside hours" auto-reply instead of AI response. Then set back to normal.
5. Open /customers. See the Active/Archived/All toggle at top.
6. Create a test customer or let Instagram create one. Click Archive button. Customer disappears from Active view. Switch to Archived → it's there. Click Unarchive → back to Active.
7. Send a DM from an archived customer's Instagram → customer should auto-unarchive.

## SUMMARY

NEW:
- backend/app/models/business_settings.py
- backend/app/services/business_hours.py
- backend/app/api/settings.py
- frontend/src/pages/SettingsPage.jsx

EDITED:
- backend/app/models/__init__.py (1 import)
- backend/app/models/customer.py (1 new column)
- backend/app/main.py (2 lines)
- backend/app/api/customers.py (archive filter + archive/unarchive endpoints)
- backend/app/api/instagram.py (business hours check + auto-unarchive)
- backend/requirements.txt (pytz)
- frontend/src/App.jsx (1 import + 1 route + 1 link)
- frontend/src/pages/CustomersPage.jsx (archive toggle + archive button + indicator)

## DO NOT
- ❌ DO NOT rewrite any existing file
- ❌ DO NOT touch persona builder, voice builder, catalog manager
- ❌ DO NOT push to git

## START NOW. Checkpoint first, then files in order.
