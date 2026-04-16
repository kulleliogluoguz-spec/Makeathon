# MASTER PROMPT: Product Catalog Upload + AI Product Recommendation

## CRITICAL RULES — READ BEFORE TOUCHING ANYTHING

1. This is an ADDITIVE feature. Do NOT rewrite, restructure, or delete any existing file.
2. Do NOT modify any existing frontend page layout or styling.
3. Do NOT push to git. All changes are local only.
4. If you find yourself writing changes to more than the files listed below, STOP and re-read this prompt.
5. Before starting, run `git add -A && git commit -m "checkpoint before catalogs feature"` to create a safety checkpoint.

## WHAT THIS FEATURE DOES

Users upload product catalog files (PDF or Excel) to a persona. The backend parses the files, extracts individual products (name, description, price, features, image), stores them in a database, and serves product images as static files. When a customer messages the business on Instagram, the AI assistant reads the catalog, intelligently selects the most relevant products based on the customer's needs, and responds with product recommendations including sending the product image via Instagram's attachment API.

## ARCHITECTURE OVERVIEW

```
User uploads catalog (PDF/Excel)
    ↓
POST /api/v1/catalogs/upload
    ↓
Backend parses file with gpt-4.1-nano
    ↓
Extracts: products[{name, description, price, features, image_url}]
    ↓
Stores products in database, linked to persona
    ↓
Images saved to backend/media/products/ (served as static files)
    ↓
On Instagram DM:
    ↓
AI sees full catalog + customer message
    ↓
Selects 0-3 best-fit products
    ↓
Sends text reply + optionally product images via Instagram API
```

## BACKEND CHANGES — NEW FILES

### File 1: `backend/app/models/catalog_models.py` (NEW FILE)

```python
"""Catalog and Product database models."""

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Catalog(Base):
    __tablename__ = "catalogs"

    id = Column(String, primary_key=True, default=gen_uuid)
    persona_id = Column(String, ForeignKey("personas.id"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, xlsx, csv, docx
    original_filename = Column(String)
    product_count = Column(Integer, default=0)
    enabled = Column(String, default="true")  # stored as string for simplicity
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="catalog", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=gen_uuid)
    catalog_id = Column(String, ForeignKey("catalogs.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    price = Column(String, default="")  # string to handle currencies, ranges
    features = Column(JSON, default=list)  # list of strings
    tags = Column(JSON, default=list)  # list of strings for categorization
    image_url = Column(String, default="")  # public URL to product image
    image_local_path = Column(String, default="")  # local path for serving
    sku = Column(String, default="")
    extra_data = Column(JSON, default=dict)  # any additional fields from catalog
    created_at = Column(DateTime, default=datetime.utcnow)

    catalog = relationship("Catalog", back_populates="products")
```

Register these models so database creates tables. In `app/models/__init__.py`, add:
```python
from app.models.catalog_models import Catalog, Product  # noqa
```

### File 2: `backend/app/services/catalog_parser.py` (NEW FILE)

```python
"""Parses PDF and Excel catalog files to extract product information using gpt-4.1-nano."""

import os
import json
import uuid
import base64
from typing import List, Dict
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

MEDIA_DIR = Path("media/products")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


async def parse_pdf(file_path: str, base_url: str) -> List[Dict]:
    """Extract products from a PDF file.
    Uses pypdf for text, pymupdf for image extraction.
    Then sends extracted content to gpt-4.1-nano to structure as products.
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")

    doc = fitz.open(file_path)
    all_text = ""
    extracted_images = []  # list of (page_num, image_path, image_url)

    for page_num, page in enumerate(doc):
        all_text += f"\n--- PAGE {page_num + 1} ---\n{page.get_text()}"

        # Extract images from page
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            filename = f"{uuid.uuid4().hex}.{image_ext}"
            local_path = MEDIA_DIR / filename
            with open(local_path, "wb") as f:
                f.write(image_bytes)

            image_url = f"{base_url.rstrip('/')}/media/products/{filename}"
            extracted_images.append({
                "page": page_num + 1,
                "local_path": str(local_path),
                "url": image_url,
                "index": img_index,
            })

    doc.close()

    # Truncate if too long
    if len(all_text) > 100000:
        all_text = all_text[:100000]

    # Ask gpt-4.1-nano to structure products
    products = await extract_products_with_llm(all_text, extracted_images)

    return products


async def parse_excel(file_path: str, base_url: str) -> List[Dict]:
    """Extract products from Excel/CSV file."""
    import pandas as pd

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # Convert each row to a dict, send all to LLM for normalization
    rows = df.to_dict(orient="records")
    rows_text = json.dumps(rows[:500], default=str)  # limit to 500 rows

    products = await extract_products_with_llm(rows_text, [])
    return products


async def extract_products_with_llm(raw_content: str, images: List[Dict]) -> List[Dict]:
    """Send raw catalog content to gpt-4.1-nano and get structured product list back."""

    images_summary = ""
    if images:
        images_summary = f"\n\n{len(images)} images were extracted from the catalog. Image URLs in order of appearance:\n"
        for i, img in enumerate(images[:50]):
            images_summary += f"[{i}] page {img['page']}: {img['url']}\n"

    system_prompt = (
        "You are a catalog parser. Extract every product from the provided catalog content. "
        "For each product, return a JSON object with these fields: "
        "name, description, price (as string, include currency), features (list of strings), "
        "tags (list of 2-5 categorization keywords), sku (if present else empty string), "
        "image_index (integer index of the best matching image from the images list, or -1 if none). "
        "Return a JSON object: {\"products\": [...]}. "
        "Extract ALL products you can find. Be thorough. Product descriptions should be 1-3 sentences. "
        "If the catalog has only 1 product, return just that one. If it has 100, return all 100."
    )

    user_message = f"Catalog content:\n\n{raw_content}{images_summary}"

    async with httpx.AsyncClient(timeout=120) as client:
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
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.1,
                "max_tokens": 8000,
                "response_format": {"type": "json_object"},
            },
        )

    if resp.status_code != 200:
        print(f"LLM parse error: {resp.status_code} {resp.text[:500]}")
        return []

    content = resp.json()["choices"][0]["message"]["content"]

    try:
        data = json.loads(content)
        products = data.get("products", [])
    except json.JSONDecodeError:
        print(f"JSON parse error on: {content[:500]}")
        return []

    # Attach image URLs based on image_index
    for p in products:
        img_idx = p.pop("image_index", -1)
        if isinstance(img_idx, int) and 0 <= img_idx < len(images):
            p["image_url"] = images[img_idx]["url"]
            p["image_local_path"] = images[img_idx]["local_path"]
        else:
            p["image_url"] = ""
            p["image_local_path"] = ""

    return products


async def parse_catalog_file(file_path: str, file_type: str, base_url: str) -> List[Dict]:
    """Route to correct parser based on file type."""
    ext = file_type.lower().replace(".", "")
    if ext == "pdf":
        return await parse_pdf(file_path, base_url)
    elif ext in ("xlsx", "xls", "csv"):
        return await parse_excel(file_path, base_url)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
```

### File 3: `backend/app/api/catalogs.py` (NEW FILE)

```python
"""Catalog upload and management API."""

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.catalog_models import Catalog, Product
from app.services.catalog_parser import parse_catalog_file

load_dotenv()

router = APIRouter()

UPLOAD_DIR = Path("media/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_base_url(request: Request) -> str:
    """Return the public base URL for serving media. Uses ngrok URL if configured."""
    base = os.getenv("PUBLIC_BASE_URL", "").strip()
    if base:
        return base
    # Fallback: use request's URL (works for localhost)
    return f"{request.url.scheme}://{request.url.netloc}"


@router.post("/catalogs/upload")
async def upload_catalog(
    request: Request,
    file: UploadFile = File(...),
    persona_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a catalog file. Returns parsed products."""

    # Save file
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "pdf"
    if ext not in ("pdf", "xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Parse
    base_url = get_base_url(request)
    try:
        products_data = await parse_catalog_file(str(file_path), ext, base_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    # Create catalog
    catalog = Catalog(
        persona_id=persona_id,
        filename=filename,
        original_filename=file.filename,
        file_type=ext,
        product_count=len(products_data),
        enabled="true",
    )
    db.add(catalog)
    await db.flush()

    # Create products
    for p in products_data:
        product = Product(
            catalog_id=catalog.id,
            name=p.get("name", "")[:500],
            description=p.get("description", "")[:5000],
            price=str(p.get("price", ""))[:100],
            features=p.get("features", []),
            tags=p.get("tags", []),
            sku=p.get("sku", "")[:100],
            image_url=p.get("image_url", ""),
            image_local_path=p.get("image_local_path", ""),
            extra_data={},
        )
        db.add(product)

    await db.commit()
    await db.refresh(catalog)

    return {
        "catalog_id": catalog.id,
        "filename": catalog.original_filename,
        "product_count": catalog.product_count,
        "products": products_data[:10],  # preview first 10
    }


@router.get("/catalogs/")
async def list_catalogs(persona_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List all catalogs, optionally filtered by persona."""
    query = select(Catalog)
    if persona_id:
        query = query.where(Catalog.persona_id == persona_id)
    result = await db.execute(query)
    catalogs = result.scalars().all()
    return [
        {
            "id": c.id,
            "persona_id": c.persona_id,
            "original_filename": c.original_filename,
            "file_type": c.file_type,
            "product_count": c.product_count,
            "enabled": c.enabled == "true",
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in catalogs
    ]


@router.get("/catalogs/{catalog_id}/products")
async def get_catalog_products(catalog_id: str, db: AsyncSession = Depends(get_db)):
    """Get all products in a catalog."""
    result = await db.execute(select(Product).where(Product.catalog_id == catalog_id))
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "features": p.features,
            "tags": p.tags,
            "image_url": p.image_url,
            "sku": p.sku,
        }
        for p in products
    ]


@router.delete("/catalogs/{catalog_id}")
async def delete_catalog(catalog_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a catalog and its products."""
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(status_code=404)
    await db.delete(catalog)
    await db.commit()
    return {"status": "deleted"}


@router.patch("/catalogs/{catalog_id}")
async def update_catalog(catalog_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Enable/disable a catalog or reassign to another persona."""
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(status_code=404)
    if "enabled" in body:
        catalog.enabled = "true" if body["enabled"] else "false"
    if "persona_id" in body:
        catalog.persona_id = body["persona_id"]
    await db.commit()
    return {"status": "updated"}
```

### Edit: `backend/app/main.py`

Add these 2 lines near the other router imports:
```python
from app.api.catalogs import router as catalogs_router
```

Add this line near the other include_router calls:
```python
app.include_router(catalogs_router, prefix="/api/v1", tags=["Catalogs"])
```

Also add static files serving. Near the top of main.py, add:
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Create media directory
Path("media").mkdir(exist_ok=True)
Path("media/products").mkdir(parents=True, exist_ok=True)
```

After `app = FastAPI(...)` line, add:
```python
app.mount("/media", StaticFiles(directory="media"), name="media")
```

### Edit: `backend/requirements.txt`

Add these if not already present:
```
pymupdf==1.24.0
pandas==2.2.0
openpyxl==3.1.2
```

### Edit: `backend/.env`

Add this line:
```
PUBLIC_BASE_URL=https://forsakenly-kinglike-thiago.ngrok-free.dev
```

### Edit: `backend/app/api/instagram.py`

Find the function that generates the reply (around `get_reply` or similar). Update it to:
1. Load the persona's products
2. Pass products to the LLM
3. If LLM recommends products, send their images via Instagram API

Add this new function to instagram.py:

```python
async def get_products_for_persona(persona_id: str):
    """Get all products from enabled catalogs assigned to this persona."""
    try:
        from app.core.database import async_session
        from app.models.catalog_models import Catalog, Product
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(Product).join(Catalog).where(
                    and_(
                        Catalog.persona_id == persona_id,
                        Catalog.enabled == "true",
                    )
                )
            )
            products = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "price": p.price,
                    "features": p.features or [],
                    "tags": p.tags or [],
                    "image_url": p.image_url,
                }
                for p in products
            ]
    except Exception as e:
        print(f"Product load error: {e}")
        return []


async def send_instagram_image(recipient_id: str, image_url: str):
    """Send an image attachment via Instagram Graph API."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "image",
                            "payload": {"url": image_url, "is_reusable": True},
                        }
                    },
                },
            )
            print(f"IG Image [{resp.status_code}]: {image_url}")
            return resp.status_code == 200
    except Exception as e:
        print(f"Send image error: {e}")
        return False
```

Modify the existing `get_reply` function (or wherever the LLM is called for Instagram replies). After it loads the persona's system_prompt, it should ALSO load products and include them in the LLM prompt:

```python
# Get persona id (use the same logic as getting the system_prompt)
# Then get products for that persona:
persona_id = persona.id if persona else None
products = await get_products_for_persona(persona_id) if persona_id else []

# Build products context
products_text = ""
if products:
    products_text = "\n\n## PRODUCT CATALOG\nYou can recommend these products to customers. If a customer asks about products or you find a good fit, recommend 1-3 from this list and put the product IDs in your response metadata:\n\n"
    for p in products:
        products_text += f"ID: {p['id']}\nName: {p['name']}\nPrice: {p['price']}\nDescription: {p['description']}\nTags: {', '.join(p['tags'])}\n\n"
    products_text += "\nWhen recommending products, respond with JSON: {\"message\": \"your reply text\", \"recommend_product_ids\": [\"id1\", \"id2\"]}. If no product fits, just use {\"message\": \"text\", \"recommend_product_ids\": []}."

# Combine
full_system_prompt = system_prompt + products_text

# Use full_system_prompt in the LLM call instead of system_prompt
# Then parse the response as JSON if products_text is non-empty
```

After getting the LLM response, if products were recommended:
```python
# After sending the text reply:
for pid in recommend_product_ids[:3]:  # max 3 images
    product = next((p for p in products if p["id"] == pid), None)
    if product and product.get("image_url"):
        await send_instagram_image(recipient_id, product["image_url"])
```

## FRONTEND — MINIMAL ADDITIVE CHANGES

### New component: `frontend/src/components/CatalogManager.jsx` (NEW FILE)

```jsx
import { useState, useEffect } from 'react';

export default function CatalogManager({ personaId }) {
  const [catalogs, setCatalogs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const loadCatalogs = async () => {
    if (!personaId) return;
    try {
      const resp = await fetch(`/api/v1/catalogs/?persona_id=${personaId}`);
      const data = await resp.json();
      setCatalogs(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadCatalogs(); }, [personaId]);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !personaId) return;
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('persona_id', personaId);
      const resp = await fetch('/api/v1/catalogs/upload', {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText);
      }
      await loadCatalogs();
    } catch (e) {
      setError(e.message || 'Upload failed');
    }
    setUploading(false);
    e.target.value = '';
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this catalog?')) return;
    await fetch(`/api/v1/catalogs/${id}`, { method: 'DELETE' });
    await loadCatalogs();
  };

  const handleToggle = async (id, enabled) => {
    await fetch(`/api/v1/catalogs/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !enabled }),
    });
    await loadCatalogs();
  };

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <label style={{
          display: 'inline-block',
          padding: '0.5rem 1rem',
          background: '#000',
          color: '#fff',
          borderRadius: '0.5rem',
          cursor: uploading ? 'wait' : 'pointer',
          opacity: uploading ? 0.5 : 1,
          fontSize: '0.875rem',
        }}>
          {uploading ? 'Uploading & parsing...' : '+ Upload Catalog (PDF, Excel, CSV)'}
          <input
            type="file"
            accept=".pdf,.xlsx,.xls,.csv"
            onChange={handleUpload}
            disabled={uploading}
            style={{ display: 'none' }}
          />
        </label>
      </div>

      {error && (
        <div style={{ color: '#dc2626', fontSize: '0.875rem', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {catalogs.length === 0 ? (
        <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>
          No catalogs uploaded yet.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {catalogs.map((c) => (
            <div
              key={c.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 1rem',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                background: c.enabled ? '#fff' : '#f9fafb',
              }}
            >
              <div>
                <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                  {c.original_filename}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {c.product_count} products · {c.file_type.toUpperCase()}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => handleToggle(c.id, c.enabled)}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.75rem',
                    borderRadius: '9999px',
                    border: '1px solid #e5e7eb',
                    background: c.enabled ? '#10b981' : '#fff',
                    color: c.enabled ? '#fff' : '#000',
                    cursor: 'pointer',
                  }}
                >
                  {c.enabled ? 'Enabled' : 'Disabled'}
                </button>
                <button
                  onClick={() => handleDelete(c.id)}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.75rem',
                    borderRadius: '9999px',
                    border: '1px solid #e5e7eb',
                    background: '#fff',
                    color: '#dc2626',
                    cursor: 'pointer',
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Edit: `frontend/src/pages/PersonaEditorPage.jsx`

Make ONLY these 2 changes:

1. Add import at top of file (next to other imports):
```jsx
import CatalogManager from '../components/CatalogManager';
```

2. Find a good spot to insert a new section — anywhere between existing sections like after the Voice section or near the bottom. Insert this:

```jsx
{/* Product Catalogs — ADDED */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1rem' }}>
  <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.25rem' }}>Product Catalogs</h2>
  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
    Upload product catalogs so the AI can recommend products during conversations.
  </p>
  <CatalogManager personaId={personaId} />
</section>
```

Replace `personaId` with whatever variable name PersonaEditorPage uses for the current persona's ID (might be `id`, `personaId`, or `persona?.id`).

DO NOT change anything else in PersonaEditorPage.

## TEST PLAN

After implementation, run these tests in order:

1. Restart backend. Verify it starts without errors:
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

2. Test upload:
```bash
curl -X POST http://localhost:8000/api/v1/catalogs/upload \
  -F "file=@/path/to/test-catalog.pdf" \
  -F "persona_id=SOME_PERSONA_ID"
```
Should return `{"catalog_id": "...", "product_count": N, "products": [...]}`

3. Test listing:
```bash
curl http://localhost:8000/api/v1/catalogs/
```

4. Test static files:
Open any `image_url` from the product response in a browser. Should display the image.

5. Frontend: open persona editor → see "Product Catalogs" section → upload a test PDF → see products counted.

6. Instagram test: DM the business account → AI should mention products from the catalog and send images.

## SUMMARY OF FILES TOUCHED

NEW:
- backend/app/models/catalog_models.py
- backend/app/services/catalog_parser.py
- backend/app/api/catalogs.py
- frontend/src/components/CatalogManager.jsx

EDITED (minimal changes only):
- backend/app/models/__init__.py (1 import line)
- backend/app/main.py (3 new lines: import, include_router, StaticFiles mount)
- backend/app/api/instagram.py (2 new functions + modified reply generation)
- backend/requirements.txt (3 new packages)
- backend/.env (1 new line)
- frontend/src/pages/PersonaEditorPage.jsx (1 import + 1 section insert)

## DO NOT

- ❌ DO NOT rewrite any existing file
- ❌ DO NOT change any layout, styling, or CSS of existing pages
- ❌ DO NOT delete or rename any existing file
- ❌ DO NOT push to git
- ❌ DO NOT add CSP headers or tags
- ❌ DO NOT modify the voice builder, voice picker, or persona form fields

## START NOW. Run `git add -A && git commit -m "checkpoint"` first, then follow the file list above in order.
