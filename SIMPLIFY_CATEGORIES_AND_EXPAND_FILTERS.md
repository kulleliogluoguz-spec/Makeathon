Two changes to Customers page and categories. Follow exactly. Do NOT rewrite any file. Do NOT push to git. Do NOT touch persona builder, voice builder, or catalog manager.

=== PART 1 — Simplify built-in categories to 3 sales-potential levels ===

Edit backend/app/services/category_seeder.py

Replace the BUILTIN_CATEGORIES list with ONLY these 3 entries:

```python
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
```

Add a cleanup function AFTER the list and BEFORE the seed function:

```python
async def cleanup_old_builtin_categories():
    """Remove built-in categories that are no longer in the current list."""
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.category import Category

    current_slugs = {c["slug"] for c in BUILTIN_CATEGORIES}
    async with async_session() as session:
        result = await session.execute(select(Category).where(Category.is_builtin == True))
        old_cats = result.scalars().all()
        for cat in old_cats:
            if cat.slug not in current_slugs:
                await session.delete(cat)
        await session.commit()
```

Update seed_builtin_categories to call cleanup first:

```python
async def seed_builtin_categories():
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
```

=== PART 2 — Advanced filters in Customers page (phone, channel, name) ===

The Customers page already has a search input and a source dropdown. Expand the search so a user can also search by PHONE NUMBER (already partially supported — verify it works), and make the channel (source) filter more prominent.

2a) Verify backend supports phone search

In backend/app/api/customers.py, the existing list_customers function already searches across display_name, handle, email, phone via the `search` parameter. Verify this works — no backend change needed unless the phone filter is missing. If phone is not in the OR clause, add it:

```python
query = query.where(
    or_(
        Customer.display_name.ilike(term),
        Customer.handle.ilike(term),
        Customer.email.ilike(term),
        Customer.phone.ilike(term),
        Customer.whatsapp_phone.ilike(term),
    )
)
```

Add Customer.whatsapp_phone to the OR if not already there. Otherwise leave as is.

2b) Expand the CustomersPage filter bar UI

In frontend/src/pages/CustomersPage.jsx, the existing search+source filters sit at the top. Change the layout to a clearer multi-field filter bar. Keep existing logic, just REPLACE the current filter bar JSX with this cleaner version:

Find this existing block (the one with the single search input and source dropdown):
```jsx
<div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
  <input ... placeholder="Search by name, handle, email, phone..." ... />
  <select ... > ... </select>
</div>
```

Replace it with:

```jsx
<div style={{
  display: 'grid',
  gridTemplateColumns: '1fr 1fr 1fr 1fr',
  gap: '0.5rem',
  marginBottom: '1rem',
}}>
  <input
    type="text"
    placeholder="Search by name..."
    value={nameFilter}
    onChange={(e) => setNameFilter(e.target.value)}
    style={{
      padding: '0.5rem 1rem', fontSize: '0.875rem',
      border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
    }}
  />
  <input
    type="text"
    placeholder="Phone number..."
    value={phoneFilter}
    onChange={(e) => setPhoneFilter(e.target.value)}
    style={{
      padding: '0.5rem 1rem', fontSize: '0.875rem',
      border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
    }}
  />
  <input
    type="text"
    placeholder="Email or @handle..."
    value={handleFilter}
    onChange={(e) => setHandleFilter(e.target.value)}
    style={{
      padding: '0.5rem 1rem', fontSize: '0.875rem',
      border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
    }}
  />
  <select
    value={sourceFilter}
    onChange={(e) => setSourceFilter(e.target.value)}
    style={{
      padding: '0.5rem 1rem', fontSize: '0.875rem',
      border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
      background: '#fff',
    }}
  >
    <option value="">All channels</option>
    <option value="instagram">Instagram</option>
    <option value="whatsapp">WhatsApp</option>
    <option value="livechat">Live Chat</option>
    <option value="manual">Manual</option>
  </select>
</div>
```

2c) Add state for the 3 separate filter fields

Find where `search` and `sourceFilter` states are declared in CustomersPage. Replace `search` with three separate states and keep `sourceFilter`:

Before:
```jsx
const [search, setSearch] = useState('');
const [sourceFilter, setSourceFilter] = useState('');
```

After:
```jsx
const [nameFilter, setNameFilter] = useState('');
const [phoneFilter, setPhoneFilter] = useState('');
const [handleFilter, setHandleFilter] = useState('');
const [sourceFilter, setSourceFilter] = useState('');
```

2d) Update the load function

Find the existing `load` async function. Replace the params-building logic:

```jsx
const load = async () => {
  const params = new URLSearchParams();
  // Combine all text filters into the single search param
  const combined = [nameFilter, phoneFilter, handleFilter].filter(Boolean).join(' ');
  if (combined) params.append('search', combined);
  if (sourceFilter) params.append('source', sourceFilter);
  if (categoryFilter) params.append('category', categoryFilter);
  try {
    const resp = await fetch(`/api/v1/customers/?${params}`);
    setCustomers(await resp.json());
  } catch (e) { console.error(e); }
};
```

Update the useEffect dependencies:
```jsx
useEffect(() => {
  load();
  const interval = setInterval(load, 15000);
  return () => clearInterval(interval);
}, [nameFilter, phoneFilter, handleFilter, sourceFilter, categoryFilter]);
```

2e) Update backend search handling for multiple terms

In backend/app/api/customers.py, the single `search` param now may receive multiple space-separated terms. Update the search logic so ALL words must match somewhere (AND logic across terms, OR across fields):

Replace the existing search block:

```python
if search:
    terms = search.strip().split()
    for word in terms:
        w = f"%{word.lower()}%"
        query = query.where(
            or_(
                Customer.display_name.ilike(w),
                Customer.handle.ilike(w),
                Customer.email.ilike(w),
                Customer.phone.ilike(w),
                Customer.whatsapp_phone.ilike(w),
            )
        )
```

This way, typing a name + a phone fragment will narrow the results correctly.

=== TEST PLAN ===

1. Restart backend. On startup, built-in categories get trimmed to the 3 new ones.

2. Check categories:
```bash
curl http://localhost:8000/api/v1/categories/ | python3 -m json.tool
```
Should show only 3 built-in + any custom you added earlier.

3. Open /customers in frontend. See the 4-column filter bar: Name, Phone, Email/Handle, Channel.

4. Test filters:
- Type a name fragment → only matching customers show
- Type a phone fragment → only customers with that phone show
- Select "Instagram" from channel dropdown → only IG customers show
- Combine name + channel → narrows to both
- Use category filter pills at top → filters by conversation category

5. AI auto-tagging on Instagram DMs will now assign only one of the 3 sales-potential categories. Send a message like "How much is it? Can I buy now?" → should get tagged "Yüksek Satış Potansiyeli" (green).

DO NOT push to git.
