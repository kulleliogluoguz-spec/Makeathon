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
