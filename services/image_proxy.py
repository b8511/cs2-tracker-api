"""
Image proxy service.
Resolves CS2 item images via the Steam Market search API, then proxies the
image from Steam's CDN (community.cloudflare.steamstatic.com).

An in-memory cache stores item_name → icon_url so the search API is only
called once per item name per server lifetime.
"""

import re
import httpx

STEAM_MARKET_SEARCH = "https://steamcommunity.com/market/search/render/"
STEAM_CDN_BASE = "https://community.cloudflare.steamstatic.com/economy/image"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# In-memory cache: item_name (lowercased) → icon_url path string
_icon_cache: dict[str, str] = {}


def normalize_name(item_name: str) -> str:
    """Derive a simple filesystem-safe key from an item name (used for R2 keys)."""
    name = re.sub(r"\s+", "_", item_name)
    name = re.sub(r"[^a-zA-Z0-9_&\-]", "", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


async def _resolve_icon_url(item_name: str, client: httpx.AsyncClient) -> str | None:
    """
    Query the Steam Market search API for `item_name` (CS2 / appid 730).
    Returns the icon_url path (relative to STEAM_CDN_BASE) or None.
    """
    cache_key = item_name.lower()
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    try:
        resp = await client.get(
            STEAM_MARKET_SEARCH,
            params={"query": item_name, "appid": "730", "norender": "1", "count": "5"},
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None

        results = resp.json().get("results", [])
        if not results:
            return None

        # Prefer an exact name match; fall back to first result
        icon_url: str | None = None
        for r in results:
            if r.get("name", "").lower() == item_name.lower():
                icon_url = r.get("asset_description", {}).get("icon_url")
                break
        if not icon_url:
            icon_url = results[0].get("asset_description", {}).get("icon_url")

        if icon_url:
            _icon_cache[cache_key] = icon_url

        return icon_url
    except (httpx.RequestError, KeyError, ValueError):
        return None


async def fetch_from_csgodb(item_name: str) -> tuple[bytes, str] | None:
    """
    Fetch the image for `item_name` from the Steam Market / Steam CDN.
    Returns (image_bytes, content_type) or None if unavailable.

    (Function name kept for backward compatibility with the router.)
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            icon_url = await _resolve_icon_url(item_name, client)
            if not icon_url:
                return None

            img_url = f"{STEAM_CDN_BASE}/{icon_url}/360fx360f"
            img_resp = await client.get(
                img_url,
                headers={"User-Agent": _USER_AGENT},
                timeout=10.0,
            )
            if img_resp.status_code == 200:
                content_type = img_resp.headers.get("content-type", "image/jpeg")
                return img_resp.content, content_type
    except httpx.RequestError:
        pass

    return None
