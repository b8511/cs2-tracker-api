from fastapi import APIRouter, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from services.steam import fetch_price

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/prices")
@limiter.limit("100/minute")
async def get_price(request: Request, name: str = Query(..., description="Steam market_hash_name")):
    """
    Fetch live price data for a CS2 item from Steam Community Market.
    Returns { success, lowest_price, median_price, volume }.
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail="Item name required")

    data = await fetch_price(name)

    if data is None or not data.get("success"):
        raise HTTPException(status_code=503, detail="Unable to fetch price from Steam")

    return data
