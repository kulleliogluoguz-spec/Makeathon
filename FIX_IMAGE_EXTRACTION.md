Replace the PDF image extraction strategy. The current approach uses fitz extract_image() which returns raw embedded bitmaps without applying PDF masks — this causes black backgrounds, halos, and artifacts around products.

The new approach: render each PDF page as a high-resolution image at 300 DPI. This produces exactly what the page looks like when viewed (with masks applied, white background, correct colors). Then we use the full rendered page as the product image for products on that page.

This is simpler AND produces much higher quality images.

In backend/app/services/catalog_parser.py, REPLACE the entire parse_pdf function with this new version:

```python
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
```

Also update the extract_products_with_llm function to expect one image per PAGE, not multiple images per page. Find this line in extract_products_with_llm:

```
images_summary = f"\n\n{len(images)} images were extracted from the catalog. Image URLs in order of appearance:\n"
```

Replace that whole block with:

```python
    images_summary = ""
    if images:
        images_summary = f"\n\n{len(images)} page images were rendered. Each page has ONE image representing it:\n"
        for i, img in enumerate(images[:50]):
            images_summary += f"[{i}] Page {img['page']}\n"
        images_summary += "\nFor each product you extract, set image_index to the page number MINUS 1 where it appears. For example, a product on page 3 has image_index = 2."
```

DO NOT change anything else. Do not touch parse_excel. Do not touch the router or models.

After applying the fix:
1. Restart the backend
2. In the frontend, delete the existing catalog
3. Re-upload the same PDF
4. Test Instagram — images should now have white backgrounds, high quality, no artifacts

Note: Each product from the same page will share the same page-level image. This is intentional and usually fine because catalog pages typically show one product prominently.

DO NOT push to git. DO NOT rewrite any other file.
