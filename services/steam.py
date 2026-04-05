"""
Steam Market price fetching service.
Mirrors the logic from the original priceoverview.ts:
  - Token bucket rate limiter (20 tokens, 1/sec refill)
  - Exponential backoff on 429/503: 2s → 32s → 62s
  - In-memory price cache with 4-hour TTL
"""

import asyncio
import time
import httpx

STEAM_APP_ID = "730"
STEAM_CURRENCY = "1"  # USD
STEAM_URL = "https://steamcommunity.com/market/priceoverview/"
RETRY_DELAYS = [2, 32, 62]  # seconds
CACHE_TTL = 4 * 60 * 60  # 4 hours in seconds

# In-memory cache: lowercased item name → {data, expires_at, fetched_at}
_price_cache: dict[str, dict] = {}


class TokenBucket:
    def __init__(self, max_tokens: int = 20, refill_rate: float = 1.0):
        self.max_tokens = max_tokens
        self.tokens = float(max_tokens)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            while self.tokens < 1:
                wait = (1 - self.tokens) / self.refill_rate
                await asyncio.sleep(wait)
                self._refill()
            self.tokens -= 1

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        added = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + added)
        self.last_refill = now


# Module-level singleton so all requests share one bucket
_bucket = TokenBucket()


async def fetch_price(item_name: str) -> dict | None:
    """
    Fetch price data from Steam Market for a CS2 item.
    Returns cached data if still fresh (< 4h old), otherwise fetches live.
    Response includes 'cached' (bool) and 'cached_at' (unix timestamp or null).
    """
    cache_key = item_name.lower()

    # Check cache first
    entry = _price_cache.get(cache_key)
    if entry and time.monotonic() < entry["expires_at"]:
        return {**entry["data"], "cached": True, "cached_at": entry["fetched_at"]}

    params = {
        "appid": STEAM_APP_ID,
        "currency": STEAM_CURRENCY,
        "market_hash_name": item_name,
    }
    headers = {
        "User-Agent": "cs-skin-tracker/1.0",
        "Accept": "application/json",
    }

    max_attempts = len(RETRY_DELAYS) + 1

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(max_attempts):
            await _bucket.acquire()

            try:
                resp = await client.get(STEAM_URL, params=params, headers=headers)
            except httpx.RequestError:
                return None

            if resp.status_code == 200:
                data = resp.json()
                fetched_at = time.time()
                _price_cache[cache_key] = {
                    "data": data,
                    "expires_at": time.monotonic() + CACHE_TTL,
                    "fetched_at": fetched_at,
                }
                return {**data, "cached": False, "cached_at": fetched_at}

            # Only retry on rate-limit responses
            if resp.status_code not in (429, 503):
                return None

            if attempt < len(RETRY_DELAYS):
                delay = RETRY_DELAYS[attempt]
                print(f"Steam rate limited, retry {attempt + 1}/{len(RETRY_DELAYS)} after {delay}s")
                await asyncio.sleep(delay)

    return None

    def __init__(self, max_tokens: int = 20, refill_rate: float = 1.0):
        self.max_tokens = max_tokens
        self.tokens = float(max_tokens)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            while self.tokens < 1:
                wait = (1 - self.tokens) / self.refill_rate
                await asyncio.sleep(wait)
                self._refill()
            self.tokens -= 1

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        added = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + added)
        self.last_refill = now


# Module-level singleton so all requests share one bucket
_bucket = TokenBucket()


async def fetch_price(item_name: str) -> dict | None:
    """
    Fetch price data from Steam Market for a CS2 item.
    Returns dict with success, lowest_price, median_price, volume or None on failure.
    """
    params = {
        "appid": STEAM_APP_ID,
        "currency": STEAM_CURRENCY,
        "market_hash_name": item_name,
    }
    headers = {
        "User-Agent": "cs-skin-tracker/1.0",
        "Accept": "application/json",
    }

    max_attempts = len(RETRY_DELAYS) + 1

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(max_attempts):
            await _bucket.acquire()

            try:
                resp = await client.get(STEAM_URL, params=params, headers=headers)
            except httpx.RequestError:
                return None

            if resp.status_code == 200:
                return resp.json()

            # Only retry on rate-limit responses
            if resp.status_code not in (429, 503):
                return None

            if attempt < len(RETRY_DELAYS):
                delay = RETRY_DELAYS[attempt]
                print(f"Steam rate limited, retry {attempt + 1}/{len(RETRY_DELAYS)} after {delay}s")
                await asyncio.sleep(delay)

    return None
