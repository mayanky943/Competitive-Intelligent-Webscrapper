import json
import pytest
from unittest.mock import AsyncMock

from app.services.cache_service import CacheService


def make_service() -> CacheService:
    svc = CacheService()
    svc._client = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_cache_hit_increments_counter():
    svc = make_service()
    payload = {"url": "https://example.com", "current_price": 29.99}
    svc._client.get.return_value = json.dumps(payload)
    svc._client.incr = AsyncMock()

    result = await svc.get_price("https://example.com")

    assert result == payload
    svc._client.incr.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_miss_increments_miss_counter():
    svc = make_service()
    svc._client.get.return_value = None
    svc._client.incr = AsyncMock()

    result = await svc.get_price("https://example.com/missing")

    assert result is None
    svc._client.incr.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_price_calls_setex():
    svc = make_service()
    svc._client.setex = AsyncMock(return_value=True)

    ok = await svc.set_price("https://example.com", {"current_price": 9.99}, ttl=3600)

    assert ok is True
    svc._client.setex.assert_awaited_once()
    args = svc._client.setex.call_args[0]
    assert args[1] == 3600  # TTL passed correctly


@pytest.mark.asyncio
async def test_unique_keys_for_different_urls():
    svc = make_service()
    key1 = svc._price_key("https://amazon.com/product/A")
    key2 = svc._price_key("https://amazon.com/product/B")

    assert key1 != key2
    assert key1.startswith("ci:price:")
    assert key2.startswith("ci:price:")


@pytest.mark.asyncio
async def test_flush_prices_deletes_keys():
    svc = make_service()
    svc._client.keys = AsyncMock(return_value=["ci:price:abc", "ci:price:def"])
    svc._client.delete = AsyncMock(return_value=2)

    count = await svc.flush_prices()

    assert count == 2


@pytest.mark.asyncio
async def test_get_stats_hit_rate():
    svc = make_service()
    svc._client.info = AsyncMock(return_value={"used_memory": 1048576, "evicted_keys": 0, "uptime_in_seconds": 600})
    svc._client.get = AsyncMock(side_effect=["80", "20"])  # hits=80, misses=20
    svc._client.keys = AsyncMock(return_value=["k1", "k2"])

    stats = await svc.get_stats()

    assert stats["hit_rate_percentage"] == 80.0
    assert stats["hits"] == 80
    assert stats["misses"] == 20
