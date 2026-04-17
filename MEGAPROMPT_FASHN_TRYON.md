# MASTER PROMPT: FASHN.ai Virtual Try-On + Fashion Video Integration

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before fashn"` as safety checkpoint.
3. Do NOT push to git.
4. Do NOT touch existing AI reply logic, persona builder, or other features.

## WHAT THIS DOES

When a customer asks to see a product on a model or requests a video showcase, the system:

1. Takes the product image from the catalog
2. Calls FASHN.ai Product-to-Model → generates a photo of a model wearing the product (~10 sec)
3. Calls FASHN.ai Image-to-Video → generates a 5-sec 1080p fashion video (~2-3 min)
4. Sends the photo immediately + sends the video when ready
5. Works on Instagram, Messenger, Telegram, LiveChat

## BACKEND — NEW FILES

### Add to requirements.txt:
```
fashn==1.0.0
```

### Edit `backend/.env`:
```
FASHN_API_KEY=your_fashn_api_key_here
```

### New file: `backend/app/services/fashn_service.py`

```python
"""FASHN.ai integration — Virtual Try-On (Product to Model) + Image to Video."""

import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

FASHN_API_KEY = os.getenv("FASHN_API_KEY", "")
BASE_URL = "https://api.fashn.ai/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {FASHN_API_KEY}",
}


async def product_to_model(product_image_url: str) -> dict:
    """
    Generate a photo of an AI model wearing the product.
    Input: product flat-lay or catalog image URL
    Output: {"success": bool, "image_url": str, "error": str}
    """
    if not FASHN_API_KEY:
        return {"success": False, "image_url": "", "error": "FASHN_API_KEY not set"}

    try:
        # Step 1: Submit the job
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/run",
                headers=HEADERS,
                json={
                    "model_name": "product-to-model",
                    "inputs": {
                        "product_image": product_image_url,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            prediction_id = data.get("id", "")

        if not prediction_id:
            return {"success": False, "image_url": "", "error": "No prediction ID returned"}

        # Step 2: Poll for result (max 60 seconds)
        for _ in range(30):
            await _async_sleep(2)
            async with httpx.AsyncClient(timeout=15) as client:
                status_resp = await client.get(
                    f"{BASE_URL}/status/{prediction_id}",
                    headers=HEADERS,
                )
                status_data = status_resp.json()

            status = status_data.get("status", "")
            if status == "completed":
                output = status_data.get("output", [])
                if output:
                    return {"success": True, "image_url": output[0], "error": ""}
                return {"success": False, "image_url": "", "error": "No output in completed response"}
            elif status == "failed":
                error = status_data.get("error", {})
                return {"success": False, "image_url": "", "error": error.get("message", "Generation failed")}

        return {"success": False, "image_url": "", "error": "Timeout waiting for result"}

    except Exception as e:
        print(f"FASHN product-to-model error: {e}")
        return {"success": False, "image_url": "", "error": str(e)}


async def image_to_video(image_url: str, duration: int = 5, resolution: str = "1080p") -> dict:
    """
    Generate a fashion video from an image (camera movement + model movement).
    Input: image URL (from product-to-model output)
    Output: {"success": bool, "video_url": str, "error": str}
    """
    if not FASHN_API_KEY:
        return {"success": False, "video_url": "", "error": "FASHN_API_KEY not set"}

    try:
        # Step 1: Submit the job
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/run",
                headers=HEADERS,
                json={
                    "model_name": "image-to-video",
                    "inputs": {
                        "image": image_url,
                        "duration": duration,
                        "resolution": resolution,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            prediction_id = data.get("id", "")

        if not prediction_id:
            return {"success": False, "video_url": "", "error": "No prediction ID returned"}

        # Step 2: Poll for result (max 5 minutes — video takes longer)
        for _ in range(150):
            await _async_sleep(2)
            async with httpx.AsyncClient(timeout=15) as client:
                status_resp = await client.get(
                    f"{BASE_URL}/status/{prediction_id}",
                    headers=HEADERS,
                )
                status_data = status_resp.json()

            status = status_data.get("status", "")
            if status == "completed":
                output = status_data.get("output", [])
                if output:
                    return {"success": True, "video_url": output[0], "error": ""}
                return {"success": False, "video_url": "", "error": "No output in completed response"}
            elif status == "failed":
                error = status_data.get("error", {})
                return {"success": False, "video_url": "", "error": error.get("message", "Video generation failed")}

        return {"success": False, "video_url": "", "error": "Timeout waiting for video"}

    except Exception as e:
        print(f"FASHN image-to-video error: {e}")
        return {"success": False, "video_url": "", "error": str(e)}


async def generate_tryon_video(product_image_url: str) -> dict:
    """
    Full pipeline: product image → model wearing it → fashion video.
    Returns {"success": bool, "model_image_url": str, "video_url": str, "error": str}
    """
    # Step 1: Product to Model
    print(f"FASHN: Starting product-to-model for {product_image_url}")
    model_result = await product_to_model(product_image_url)

    if not model_result["success"]:
        return {
            "success": False,
            "model_image_url": "",
            "video_url": "",
            "error": f"Try-on failed: {model_result['error']}",
        }

    model_image_url = model_result["image_url"]
    print(f"FASHN: Product-to-model complete: {model_image_url}")

    # Step 2: Image to Video
    print(f"FASHN: Starting image-to-video...")
    video_result = await image_to_video(model_image_url)

    if not video_result["success"]:
        # Return just the model image if video fails
        return {
            "success": True,
            "model_image_url": model_image_url,
            "video_url": "",
            "error": f"Video failed but try-on image available: {video_result['error']}",
        }

    print(f"FASHN: Video complete: {video_result['video_url']}")
    return {
        "success": True,
        "model_image_url": model_image_url,
        "video_url": video_result["video_url"],
        "error": "",
    }


async def _async_sleep(seconds):
    import asyncio
    await asyncio.sleep(seconds)
```

### New file: `backend/app/api/tryon.py`

```python
"""Virtual try-on API endpoint — trigger try-on + video for a product."""

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.catalog_models import Product
from app.services.fashn_service import generate_tryon_video, product_to_model, image_to_video

router = APIRouter()


@router.post("/tryon/{product_id}")
async def trigger_tryon(product_id: str, body: dict = {}, db: AsyncSession = Depends(get_db)):
    """
    Trigger virtual try-on for a product.
    Optional body: {"video": true} to also generate video.
    Returns model image URL and optionally video URL.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.image_url:
        raise HTTPException(status_code=400, detail="Product has no image")

    want_video = body.get("video", True)

    if want_video:
        tryon_result = await generate_tryon_video(product.image_url)
    else:
        tryon_result_img = await product_to_model(product.image_url)
        tryon_result = {
            "success": tryon_result_img["success"],
            "model_image_url": tryon_result_img.get("image_url", ""),
            "video_url": "",
            "error": tryon_result_img.get("error", ""),
        }

    return {
        "product_id": product_id,
        "product_name": product.name,
        **tryon_result,
    }


@router.post("/tryon/image-only/{product_id}")
async def trigger_tryon_image_only(product_id: str, db: AsyncSession = Depends(get_db)):
    """Just generate the try-on image, no video."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product or not product.image_url:
        raise HTTPException(status_code=404, detail="Product not found or no image")

    tryon_result = await product_to_model(product.image_url)
    return {
        "product_id": product_id,
        "product_name": product.name,
        "success": tryon_result["success"],
        "image_url": tryon_result.get("image_url", ""),
        "error": tryon_result.get("error", ""),
    }
```

### Edit: `backend/app/main.py`

Add import:
```python
from app.api.tryon import router as tryon_router
```

Add include_router:
```python
app.include_router(tryon_router, prefix="/api/v1", tags=["TryOn"])
```

## INTEGRATE INTO AI REPLY FLOW

### Edit: `backend/app/api/instagram.py`

The AI needs to know it can trigger virtual try-on. Add this to the products_text section (where the product catalog prompt is built):

Find where products_text is built and add this line at the end of the products instruction:

```python
products_text += '\n\nVIRTUAL TRY-ON: If the customer asks to see a product on a model, asks "how would this look on me", or requests a video/demo of a product, include "tryon_product_id" in your JSON response with the product ID. Example: {"message": "Let me show you how it looks!", "recommend_product_ids": ["id1"], "tryon_product_id": "id1"}\nOnly use tryon_product_id when the customer EXPLICITLY asks to see it on a person or requests a video. Do NOT use it for normal product recommendations.'
```

Then, AFTER parsing the AI response and sending the normal reply + images, add the try-on handling:

```python
# Handle virtual try-on request
tryon_pid = None
if products:
    try:
        if isinstance(parsed, dict):
            tryon_pid = parsed.get("tryon_product_id", None)
    except Exception:
        pass

if tryon_pid:
    import asyncio
    try:
        # Find the product
        tryon_product = next((p for p in products if p["id"] == tryon_pid), None)
        if tryon_product and tryon_product.get("image_url"):
            # Send "preparing" message
            await send_reply(sender_id, "✨ Preparing a virtual try-on for you... This may take a moment!")

            # Run try-on in background (don't block the webhook response)
            asyncio.create_task(_handle_tryon_async(sender_id, tryon_product))
    except Exception as e:
        print(f"Try-on trigger error: {e}")
```

Add this async function at the end of instagram.py (or near the other helper functions):

```python
async def _handle_tryon_async(sender_id: str, product: dict):
    """Background task: generate try-on image + video and send to customer."""
    try:
        from app.services.fashn_service import product_to_model, image_to_video

        # Step 1: Generate try-on image
        model_result = await product_to_model(product["image_url"])
        if model_result["success"]:
            # Send the try-on image immediately
            await send_instagram_image(sender_id, model_result["image_url"])
            await send_reply(sender_id, f"👆 Here's how {product['name']} looks on a model!")

            # Step 2: Generate video
            await send_reply(sender_id, "🎬 Generating a 360° video for you... (this takes about 2 minutes)")
            video_result = await image_to_video(model_result["image_url"])
            if video_result["success"]:
                # Send video URL (Instagram can't embed videos via API, send as link)
                await send_reply(sender_id, f"🎥 Your fashion video is ready!\n{video_result['video_url']}")
            else:
                print(f"Video generation failed: {video_result['error']}")
        else:
            await send_reply(sender_id, "Sorry, I couldn't generate the try-on image right now. Please try again later!")
            print(f"Try-on failed: {model_result['error']}")
    except Exception as e:
        print(f"Try-on async error: {e}")
        await send_reply(sender_id, "Sorry, there was an issue generating the try-on. Please try again!")
```

### Apply the same logic to `backend/app/api/messenger.py`:

Add the same products_text addition for VIRTUAL TRY-ON instruction.

Add the same tryon_pid parsing after the AI response.

Add the same _handle_tryon_async function (but using send_messenger_reply and send_messenger_image instead).

### Apply to `backend/app/api/livechat.py`:

In the generate_livechat_reply function, add the tryon_product_id parsing. If present, add the try-on image and video URLs to the response sent back via WebSocket.

### Apply to `backend/app/api/telegram.py`:

Same pattern — add VIRTUAL TRY-ON instruction to products_text, parse tryon_product_id, run async try-on task using send_telegram_message and send_telegram_image.

## FRONTEND — Add Try-On button in Conversations

### Edit: `frontend/src/pages/ConversationsPage.jsx`

In the conversation detail panel, where product images/recommendations are shown, add a "Try On" button next to each product. If the user clicks it, trigger the try-on API:

Find where the conversation messages are rendered. After the message list, add a small section if the conversation has products mentioned:

```jsx
{detail.products_mentioned && detail.products_mentioned.length > 0 && (
  <div style={{ marginTop: '0.75rem', padding: '0.75rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', background: '#f9fafb' }}>
    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>PRODUCTS IN CONVERSATION</div>
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
      {detail.products_mentioned.slice(0, 5).map((pid) => (
        <button
          key={pid}
          onClick={async () => {
            if (!confirm('Generate virtual try-on + video? This uses FASHN.ai credits.')) return;
            const resp = await fetch(`/api/v1/tryon/${pid}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ video: true }),
            });
            const data = await resp.json();
            if (data.success) {
              alert(`Try-on generated!\nImage: ${data.model_image_url}\nVideo: ${data.video_url || 'Generating...'}`);
            } else {
              alert(`Error: ${data.error}`);
            }
          }}
          style={{
            padding: '4px 12px', fontSize: '0.7rem',
            background: '#8b5cf6', color: '#fff',
            border: 'none', borderRadius: '9999px', cursor: 'pointer',
          }}
        >👗 Try On: {pid.slice(0, 8)}...</button>
      ))}
    </div>
  </div>
)}
```

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before fashn"`
2. Get FASHN API key: go to fashn.ai → sign up → developer dashboard → get API key
3. Add to .env: FASHN_API_KEY=your_key
4. pip install fashn (or just use httpx which is already installed)
5. Restart backend.
6. Test API directly:
```bash
curl -X POST http://localhost:8000/api/v1/tryon/PRODUCT_ID \
  -H "Content-Type: application/json" \
  -d '{"video": false}'
```
(Replace PRODUCT_ID with an actual product ID from your catalog)

7. Test via Instagram: send "Can you show me how this t-shirt looks on a model?" → AI should respond and trigger try-on.
8. Check: try-on image sent → "generating video" message → video URL sent.

## SUMMARY

NEW:
- backend/app/services/fashn_service.py
- backend/app/api/tryon.py

EDITED:
- backend/app/main.py (2 lines)
- backend/.env (1 line)
- backend/requirements.txt (1 line)
- backend/app/api/instagram.py (try-on instruction in prompt + tryon_pid parsing + async handler)
- backend/app/api/messenger.py (same)
- backend/app/api/livechat.py (same)
- backend/app/api/telegram.py (same)
- frontend/src/pages/ConversationsPage.jsx (try-on button)

## DO NOT
- ❌ DO NOT rewrite any file
- ❌ DO NOT push to git
- ❌ DO NOT change existing AI reply logic — only ADD try-on handling after it

## START NOW. Checkpoint first.
