from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import CacheStats
from app.services.cache_service import cache_service

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats", response_model=CacheStats, summary="Cache hit/miss statistics")
async def get_cache_stats():
    stats = await cache_service.get_stats()
    if not stats:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return CacheStats(**stats)


@router.delete(
    "/prices",
    summary="Flush all cached pricing data",
    response_description="Number of keys cleared",
)
async def flush_price_cache():
    count = await cache_service.flush_prices()
    return {"message": f"Cleared {count} cached price entries"}


@router.delete("/stats", summary="Reset hit/miss counters")
async def reset_stats():
    await cache_service.reset_stats()
    return {"message": "Cache statistics reset"}


@router.get("/ttl", summary="Remaining TTL for a cached URL")
async def get_ttl(url: str = Query(..., description="URL to inspect")):
    ttl = await cache_service.get_ttl(url)
    return {
        "url": url,
        "ttl_seconds": ttl,
        "cached": ttl > 0,
        "expires_in": f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else "not cached",
    }
