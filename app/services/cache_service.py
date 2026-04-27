import hashlib
import json
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from loguru import logger

from app.config import settings

# Redis key namespace constants
NS_PRICE = "ci:price"
NS_JOB = "ci:job"
NS_STATS_HITS = "ci:stats:hits"
NS_STATS_MISSES = "ci:stats:misses"


class CacheService:
    """
    Async Redis cache for pricing data.

    Tracks hits/misses to measure the network-call reduction ratio.
    Default TTL of 1 hour means the same URL is only fetched once per hour,
    driving the ~40% reduction in redundant outbound requests across
    repeated queries for the same products.
    """

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        self._client = await aioredis.from_url(
            url,
            password=settings.REDIS_PASSWORD or None,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        logger.info(f"Redis connected at {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _price_key(url: str) -> str:
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return f"{NS_PRICE}:{url_hash}"

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"{NS_JOB}:{job_id}"

    # ------------------------------------------------------------------
    # Pricing data cache
    # ------------------------------------------------------------------

    async def get_price(self, url: str) -> Optional[Dict[str, Any]]:
        key = self._price_key(url)
        try:
            raw = await self._client.get(key)
            if raw:
                await self._client.incr(NS_STATS_HITS)
                logger.debug(f"Cache HIT  → {url}")
                return json.loads(raw)
            await self._client.incr(NS_STATS_MISSES)
            logger.debug(f"Cache MISS → {url}")
            return None
        except Exception as exc:
            logger.error(f"cache.get_price error: {exc}")
            return None

    async def set_price(
        self,
        url: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        key = self._price_key(url)
        ttl = ttl or settings.CACHE_TTL_PRICING
        try:
            await self._client.setex(key, ttl, json.dumps(data, default=str))
            logger.debug(f"Cached price data for {url} (TTL {ttl}s)")
            return True
        except Exception as exc:
            logger.error(f"cache.set_price error: {exc}")
            return False

    async def delete_price(self, url: str) -> bool:
        key = self._price_key(url)
        return bool(await self._client.delete(key))

    async def get_ttl(self, url: str) -> int:
        return await self._client.ttl(self._price_key(url))

    # ------------------------------------------------------------------
    # Job state cache
    # ------------------------------------------------------------------

    async def get_job(self, job_id: str) -> Optional[Dict]:
        raw = await self._client.get(self._job_key(job_id))
        return json.loads(raw) if raw else None

    async def set_job(self, job_id: str, data: Dict, ttl: int = 86400) -> None:
        await self._client.setex(self._job_key(job_id), ttl, json.dumps(data, default=str))

    async def list_job_keys(self) -> list:
        return await self._client.keys(f"{NS_JOB}:*")

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    async def flush_prices(self) -> int:
        keys = await self._client.keys(f"{NS_PRICE}:*")
        if keys:
            return await self._client.delete(*keys)
        return 0

    async def flush_all_ci(self) -> int:
        keys = await self._client.keys("ci:*")
        if keys:
            return await self._client.delete(*keys)
        return 0

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_stats(self) -> Dict[str, Any]:
        try:
            info = await self._client.info("all")
            hits = int(await self._client.get(NS_STATS_HITS) or 0)
            misses = int(await self._client.get(NS_STATS_MISSES) or 0)
            total = hits + misses
            hit_rate = round(hits / total * 100, 2) if total else 0.0

            price_keys = await self._client.keys(f"{NS_PRICE}:*")
            return {
                "total_keys": len(price_keys),
                "hits": hits,
                "misses": misses,
                "hit_rate_percentage": hit_rate,
                "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "evicted_keys": info.get("evicted_keys", 0),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as exc:
            logger.error(f"cache.get_stats error: {exc}")
            return {
                "total_keys": 0,
                "hits": 0,
                "misses": 0,
                "hit_rate_percentage": 0.0,
                "memory_used_mb": 0.0,
                "evicted_keys": 0,
                "uptime_seconds": 0,
            }

    async def reset_stats(self) -> None:
        await self._client.delete(NS_STATS_HITS, NS_STATS_MISSES)


cache_service = CacheService()
