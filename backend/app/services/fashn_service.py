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
    Full pipeline: product image -> model wearing it -> fashion video.
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
