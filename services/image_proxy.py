"""
Image proxy service.
Resolves CS2 item images via the Steam Market listing render endpoint (exact
item lookup), falling back to the search API if needed. Then proxies the image
from Steam's CDN (community.cloudflare.steamstatic.com).

In-memory cache: item_name → icon_url, populated on first fetch.
"""

import re
import httpx

STEAM_LISTING_RENDER = "https://steamcommunity.com/market/listings/730/{name}/render"
STEAM_MARKET_SEARCH = "https://steamcommunity.com/market/search/render/"
STEAM_CDN_BASE = "https://community.cloudflare.steamstatic.com/economy/image"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# In-memory cache: item_name (lowercased) → icon_url path string
_icon_cache: dict[str, str] = {}


def normalize_name(item_name: str) -> str:
    """Derive a simple filesystem-safe key from an item name (used for R2 keys)."""
    name = re.sub(r"\s+", "_", item_name)
    name = re.sub(r"[^a-zA-Z0-9_&\-]", "", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


async def _resolve_via_listing(item_name: str, client: httpx.AsyncClient) -> str | None:
    """
    Use the market listing render endpoint for the exact item name.
    This is authoritative — it only returns data for that specific item.
    """
    url = STEAM_LISTING_RENDER.format(name=item_name)
    try:
        resp = await client.get(
            url,
            params={"start": "0", "count": "1", "currency": "1", "language": "english"},
            headers={"User-Agent": _USER_AGENT},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None
        assets = resp.json().get("assets", {})
        for contexts in assets.values():
            for items in contexts.values():
                for item in items.values():
                    icon_url = item.get("icon_url")
                    if icon_url:
                        return icon_url
    except (httpx.RequestError, KeyError, ValueError):
        pass
    return None


async def _resolve_via_search(item_name: str, client: httpx.AsyncClient) -> str | None:
    """
    Fallback: search the Steam Market and look for an exact name match.
    """
    try:
        resp = await client.get(
            STEAM_MARKET_SEARCH,
            params={"query": item_name, "appid": "730", "norender": "1", "count": "10"},
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None
        results = resp.json().get("results", [])
        for r in results:
            if r.get("hash_name", "").lower() == item_name.lower() or r.get("name", "").lower() == item_name.lower():
                icon_url = r.get("asset_description", {}).get("icon_url")
                if icon_url:
                    return icon_url
    except (httpx.RequestError, KeyError, ValueError):
        pass
    return None


async def _resolve_icon_url(item_name: str, client: httpx.AsyncClient) -> str | None:
    cache_key = item_name.lower()
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    icon_url = await _resolve_via_listing(item_name, client)
    if not icon_url:
        icon_url = await _resolve_via_search(item_name, client)

    if icon_url:
        _icon_cache[cache_key] = icon_url

    return icon_url


async def fetch_from_csgodb(item_name: str) -> tuple[bytes, str] | None:
    """
    Fetch the image for `item_name` from Steam CDN.
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
