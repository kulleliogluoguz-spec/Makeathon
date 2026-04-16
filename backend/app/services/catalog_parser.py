"""Parses PDF and Excel catalog files to extract product information using gpt-4.1-nano."""

import os
import json
import uuid
from typing import List, Dict
from pathlib import Path
import httpx
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

MEDIA_DIR = Path("media/products")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


async def parse_pdf(file_path: str, base_url: str) -> List[Dict]:
    """Extract products from a PDF file.
    Renders each page at high DPI for clean product images (masks applied, white background).
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")

    doc = fitz.open(file_path)
    all_text = ""
    page_images = []  # one image per page

    for page_num, page in enumerate(doc):
        all_text += f"\n--- PAGE {page_num + 1} ---\n{page.get_text()}"

        # Render page at 300 DPI (default is 72, so zoom = 300/72 ≈ 4.17)
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # alpha=False forces white background

        filename = f"{uuid.uuid4().hex}.jpg"
        local_path = MEDIA_DIR / filename

        # Save as JPG with high quality
        pix.save(str(local_path), output="jpg", jpg_quality=95)

        image_url = f"{base_url.rstrip('/')}/media/products/{filename}"
        page_images.append({
            "page": page_num + 1,
            "local_path": str(local_path),
            "url": image_url,
            "index": page_num,
        })

    doc.close()

    # Truncate if too long
    if len(all_text) > 100000:
        all_text = all_text[:100000]

    # Ask gpt-4.1-nano to structure products. Each product will be matched to the page it appears on.
    products = await extract_products_with_llm(all_text, page_images)

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
        images_summary = f"\n\n{len(images)} page images were rendered. Each page has ONE image representing it:\n"
        for i, img in enumerate(images[:50]):
            images_summary += f"[{i}] Page {img['page']}\n"
        images_summary += "\nFor each product you extract, set image_index to the page number MINUS 1 where it appears. For example, a product on page 3 has image_index = 2."

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
