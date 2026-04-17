Two changes to the FASHN try-on integration:

1. Send videos DIRECTLY as video attachments, not as URL text messages
2. Trigger try-on automatically with EVERY product recommendation, not only when the customer explicitly asks

Do NOT rewrite files. Do NOT push to git.

## CHANGE 1 — Send video as attachment

In backend/app/api/instagram.py, add a new function to send video via Instagram API:

```python
async def send_instagram_video(recipient_id: str, video_url: str):
    """Send a video via Instagram Messaging API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={
                    "Authorization": f"Bearer {INSTAGRAM_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "video",
                            "payload": {"url": video_url},
                        }
                    },
                },
            )
            print(f"IG Video [{resp.status_code}]: {video_url[:50]}")
    except Exception as e:
        print(f"IG video send error: {e}")
```

In backend/app/api/messenger.py, add:

```python
async def send_messenger_video(recipient_id: str, video_url: str):
    """Send a video via Messenger API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                headers={
                    "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "video",
                            "payload": {"url": video_url, "is_reusable": True},
                        }
                    },
                },
            )
            print(f"Messenger Video [{resp.status_code}]: {video_url[:50]}")
    except Exception as e:
        print(f"Messenger video send error: {e}")
```

In backend/app/services/telegram_sender.py, add:

```python
async def send_telegram_video(chat_id: str, video_url: str, caption: str = "") -> dict:
    """Send a video via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendVideo",
                json={"chat_id": chat_id, "video": video_url, "caption": caption},
            )
            data = resp.json()
            return {"success": data.get("ok", False)}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## CHANGE 2 — Update _handle_tryon_async to send video directly

In instagram.py, find the _handle_tryon_async function. Replace the line that sends the video URL as text:

OLD:
```python
await send_reply(sender_id, f"🎥 Your fashion video is ready!\n{video_result['video_url']}")
```

NEW:
```python
await send_instagram_video(sender_id, video_result["video_url"])
```

Do the same in messenger.py:
```python
await send_messenger_video(sender_id, video_result["video_url"])
```

And telegram.py:
```python
from app.services.telegram_sender import send_telegram_video
await send_telegram_video(sender_id, video_result["video_url"], f"🎥 {product['name']} - Fashion Video")
```

## CHANGE 3 — Trigger try-on with EVERY product recommendation automatically

In instagram.py, find where recommend_product_ids are processed and images are sent. AFTER sending all product images, add try-on for the FIRST recommended product:

```python
# After sending product images, auto-trigger try-on for first product
if recommend_ids and len(recommend_ids) > 0:
    first_product = next((p for p in products if p["id"] == recommend_ids[0]), None)
    if first_product and first_product.get("image_url"):
        import asyncio
        asyncio.create_task(_handle_tryon_async(sender_id, first_product))
```

REMOVE the old tryon_pid logic that only triggers when the customer explicitly asks. The try-on should now happen automatically with every product recommendation.

Remove these lines (or comment them out):
- The `tryon_pid = parsed.get("tryon_product_id", None)` parsing
- The `if tryon_pid:` block that checks for explicit try-on requests

Also REMOVE the "VIRTUAL TRY-ON" instruction from products_text. The AI no longer needs to decide when to trigger try-on — it always happens automatically.

Do the same changes in messenger.py, livechat.py, and telegram.py:
- After sending product images, auto-trigger try-on for first recommended product
- Remove tryon_product_id parsing and related code
- Remove VIRTUAL TRY-ON instruction from products_text

## CHANGE 4 — Update the "preparing" message

In _handle_tryon_async, change the messages to be more natural. Instead of asking permission, just do it:

```python
async def _handle_tryon_async(sender_id: str, product: dict):
    """Background task: generate try-on image + video and send to customer."""
    try:
        from app.services.fashn_service import product_to_model, image_to_video

        # Step 1: Generate try-on image
        model_result = await product_to_model(product["image_url"])
        if model_result["success"]:
            # Send the try-on image
            await send_instagram_image(sender_id, model_result["image_url"])

            # Step 2: Generate video (silently, no "generating" message)
            video_result = await image_to_video(model_result["image_url"])
            if video_result["success"]:
                await send_instagram_video(sender_id, video_result["video_url"])
            else:
                print(f"Video generation failed: {video_result['error']}")
        else:
            print(f"Try-on failed: {model_result['error']}")
    except Exception as e:
        print(f"Try-on async error: {e}")
```

Notice: NO "preparing" or "generating" messages. The experience is:
1. Customer asks about a product
2. AI sends text reply + product catalog image
3. A few seconds later: try-on model image appears
4. A couple minutes later: video appears

Clean and seamless. No noise.

Apply this same clean _handle_tryon_async pattern to messenger.py and telegram.py (using their respective send functions).

## DO NOT
- ❌ DO NOT rewrite files
- ❌ DO NOT push to git
- ❌ DO NOT change the AI prompt or reply logic — only add try-on AFTER the normal reply flow

## START NOW
