Fix the extracted product images: add a white background to transparent PNGs and improve quality.

In backend/app/services/catalog_parser.py, find the section in parse_pdf that extracts images from each page. Replace the image saving block with this version that uses Pillow to flatten transparency and upscale:

```python
from PIL import Image
from io import BytesIO

# Inside the image extraction loop, after you get image_bytes and image_ext:
try:
    img = Image.open(BytesIO(image_bytes))

    # Skip tiny images (likely icons or noise)
    if img.width < 100 or img.height < 100:
        continue

    # Convert to RGBA to handle transparency, then flatten on white background
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGBA')
        white_bg = Image.new('RGB', img.size, (255, 255, 255))
        white_bg.paste(img, mask=img.split()[-1])  # alpha channel as mask
        img = white_bg
    else:
        img = img.convert('RGB')

    # Upscale small images for better quality on Instagram
    if img.width < 600:
        scale = 600 / img.width
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

    filename = f"{uuid.uuid4().hex}.jpg"
    local_path = MEDIA_DIR / filename
    img.save(local_path, "JPEG", quality=95, optimize=True)
except Exception as e:
    print(f"Image process error: {e}")
    continue
```

Add this import at the top of catalog_parser.py if not already present:
```python
from PIL import Image
from io import BytesIO
```

Make sure Pillow is installed. Add to requirements.txt if missing:
```
Pillow==10.2.0
```

Then run:
```
pip install Pillow
```

After the change, inform me so I can delete the existing catalog and re-upload it — because old images are already saved with black backgrounds and will not be regenerated automatically.

DO NOT change anything else in the file. DO NOT modify any other file. DO NOT push to git. DO NOT rewrite the parser — only update the image saving block.
