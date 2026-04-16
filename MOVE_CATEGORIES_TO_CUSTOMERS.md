Change the category feature: remove the standalone Categories page, move the filter into the Customers page. AI auto-tagging stays (backend), and user just sees a category filter bar on the Customers page.

RULES:
- Do NOT rewrite any file
- Do NOT push to git
- Do NOT touch persona builder, voice builder, catalog manager

CHANGES:

1. Remove the CategoriesPage nav link and route from frontend/src/App.jsx.
   - Find the `<Link to="/categories">Categories</Link>` — DELETE it
   - Find `<Route path="/categories" element={<CategoriesPage />} />` — DELETE it
   - Find `import CategoriesPage from './pages/CategoriesPage';` — DELETE it
   - Do not touch other links, routes, or imports

2. Update the Customers backend endpoint to support filtering by category tag.
   In backend/app/api/customers.py, update the `list_customers` endpoint:
   - Add a new query parameter: `category: Optional[str] = Query(None)`
   - After fetching customers, filter them by category: for each customer, look up their ConversationState (matching instagram_sender_id or whatsapp_phone), and keep only customers where at least one of their conversations has the selected category slug in its `categories` field.

   Implementation:
   ```python
   @router.get("/customers/")
   async def list_customers(
       search: Optional[str] = Query(None),
       tag: Optional[str] = Query(None),
       source: Optional[str] = Query(None),
       category: Optional[str] = Query(None),
       db: AsyncSession = Depends(get_db),
   ):
       # ... existing search/source logic stays ...
       result = await db.execute(query)
       customers = result.scalars().all()

       # existing tag filter
       if tag:
           customers = [c for c in customers if tag in (c.tags or [])]

       # NEW: filter by conversation category
       if category:
           from app.models.conversation_state import ConversationState
           # Load all conversation states with this category
           conv_result = await db.execute(select(ConversationState))
           all_convs = conv_result.scalars().all()
           matching_ids = set()
           for conv in all_convs:
               if category in (conv.categories or []):
                   if conv.sender_id:
                       matching_ids.add(conv.sender_id)
           # Filter customers: keep only those whose external IDs match
           customers = [
               c for c in customers
               if c.instagram_sender_id in matching_ids or c.whatsapp_phone in matching_ids
           ]

       return [_serialize(c) for c in customers]
   ```

3. Update CustomersPage.jsx to add the category filter bar.

   At the top of the component, add state for categories and activeCategory:
   ```jsx
   const [allCategories, setAllCategories] = useState([]);
   const [categoryFilter, setCategoryFilter] = useState('');

   useEffect(() => {
     fetch('/api/v1/categories/').then(r => r.json()).then(setAllCategories).catch(() => {});
   }, []);
   ```

   Update the `load` function to include the category filter:
   ```jsx
   const load = async () => {
     const params = new URLSearchParams();
     if (search) params.append('search', search);
     if (sourceFilter) params.append('source', sourceFilter);
     if (categoryFilter) params.append('category', categoryFilter);
     try {
       const resp = await fetch(`/api/v1/customers/?${params}`);
       setCustomers(await resp.json());
     } catch (e) { console.error(e); }
   };
   ```

   Add `categoryFilter` to the useEffect dependencies so the list reloads when the filter changes.

   Insert a category filter bar BELOW the existing search/source filters and ABOVE the customer list:
   ```jsx
   {allCategories.length > 0 && (
     <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
       <button
         onClick={() => setCategoryFilter('')}
         style={{
           fontSize: '0.75rem', padding: '4px 12px', borderRadius: '9999px',
           background: !categoryFilter ? '#000' : '#fff',
           color: !categoryFilter ? '#fff' : '#374151',
           border: '1px solid #e5e7eb', cursor: 'pointer',
         }}
       >All categories</button>
       {allCategories.map((c) => (
         <button
           key={c.id}
           onClick={() => setCategoryFilter(categoryFilter === c.slug ? '' : c.slug)}
           style={{
             fontSize: '0.75rem', padding: '4px 12px', borderRadius: '9999px',
             background: categoryFilter === c.slug ? c.color : '#fff',
             color: categoryFilter === c.slug ? '#fff' : '#374151',
             border: '1px solid #e5e7eb', cursor: 'pointer',
           }}
         >{c.name}</button>
       ))}
     </div>
   )}
   ```

4. Optional: you can DELETE the file frontend/src/pages/CategoriesPage.jsx since it's no longer used. Or leave it — no harm if orphaned.

After changes:
- /categories URL should 404 (no route)
- Navbar has no "Categories" link
- Customers page has a category filter bar that shows all built-in + custom categories as colored pills
- Clicking a category pill filters the customer list to only customers who have at least one conversation tagged with that category
- Clicking "All categories" clears the filter
- AI auto-tagging continues to work in the Instagram webhook (no backend logic removed)

DO NOT remove any backend file — the categories API and auto-tagging service stay in place. Only the frontend Categories PAGE and its nav entry are removed.

DO NOT push to git.
