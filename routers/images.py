import asyncio
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from services.image_proxy import fetch_from_csgodb, normalize_name
from services import r2_storage

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Cache-Control for served images: 24h browser, 7d CDN
IMAGE_CACHE = "public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400"


@router.get("/images")
@limiter.limit("200/minute")
async def get_image(request: Request, n: str = Query(..., description="CS2 item name")):
    """
    Serve an item image.
    Strategy:
      1. Try fetching live from csgodatabase.com (no Referer — bypasses hotlink protection)
      2. Fall back to Cloudflare R2 bucket if step 1 fails
      3. 404 if neither source has the image
    """
    if not n.strip():
        raise HTTPException(status_code=400, detail="Item name required")

    key = f"{normalize_name(n)}.webp"

    # --- Strategy 1: live proxy from csgodatabase.com ---
    result = await fetch_from_csgodb(n)
    if result:
        image_bytes, content_type = result

        # Opportunistically cache in R2 in the background (fire-and-forget)
        if r2_storage.is_configured():
            asyncio.create_task(_cache_to_r2(key, image_bytes, content_type))

        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={"Cache-Control": IMAGE_CACHE},
        )

    # --- Strategy 2: R2 fallback ---
    if r2_storage.is_configured():
        cached = r2_storage.get_image(key)
        if cached:
            return Response(
                content=cached,
                media_type="image/webp",
                headers={"Cache-Control": IMAGE_CACHE},
            )

    raise HTTPException(status_code=404, detail="Image not found")


async def _cache_to_r2(key: str, data: bytes, content_type: str) -> None:
    """Background task: store a freshly proxied image in R2 for future fallback."""
    try:
        await asyncio.to_thread(r2_storage.put_image, key, data, content_type)
    except Exception as e:
        print(f"R2 cache write failed for {key}: {e}")
