import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from loguru import logger

from app.config import settings
from app.models.schemas import BatchScrapeRequest, JobStatus, PriceData, ScrapeJob, ScrapeRequest
from app.scrapers.async_scraper import AsyncPriceScraper
from app.services.cache_service import cache_service
from app.services.job_service import job_service
from app.utils.rate_limiter import AsyncRateLimiter

_rate_limiter = AsyncRateLimiter(
    requests_per_window=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
)

_PRICE_FIELDS = set(PriceData.model_fields.keys())


def _to_price_data(raw: Dict[str, Any]) -> PriceData:
    return PriceData(**{k: v for k, v in raw.items() if k in _PRICE_FIELDS})


class ScraperService:

    # ------------------------------------------------------------------
    # Single-URL scrape
    # ------------------------------------------------------------------

    async def scrape_url(self, request: ScrapeRequest) -> Optional[Dict[str, Any]]:
        url = request.url

        # 1. Check cache (skip when force_refresh=True)
        if request.use_cache and not request.force_refresh:
            cached = await cache_service.get_price(url)
            if cached:
                return {**cached, "from_cache": True}

        # 2. Rate-limit per domain then fetch
        await _rate_limiter.acquire(urlparse(url).netloc)

        async with AsyncPriceScraper() as scraper:
            result = await scraper.scrape(url, custom_selectors=request.custom_selectors)

        if result and request.use_cache:
            await cache_service.set_price(url, result)

        return {**result, "from_cache": False} if result else None

    # ------------------------------------------------------------------
    # Batch scrape (runs as a background task)
    # ------------------------------------------------------------------

    async def run_batch_job(self, job: ScrapeJob, request: BatchScrapeRequest) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        await job_service.save(job)

        semaphore = asyncio.Semaphore(request.concurrent_limit)

        async def process(url: str) -> None:
            async with semaphore:
                try:
                    # Cache check
                    if request.use_cache and not request.force_refresh:
                        cached = await cache_service.get_price(url)
                        if cached:
                            job.cache_hits += 1
                            job.results.append(_to_price_data(cached))
                            return

                    job.cache_misses += 1
                    await _rate_limiter.acquire(urlparse(url).netloc)

                    async with AsyncPriceScraper() as scraper:
                        result = await scraper.scrape(
                            url,
                            custom_selectors=request.custom_selectors,
                        )

                    if result:
                        if request.use_cache:
                            await cache_service.set_price(url, result)
                        job.results.append(_to_price_data(result))
                    else:
                        job.errors.append({"url": url, "error": "No data extracted"})

                except Exception as exc:
                    logger.error(f"Batch scrape error [{url}]: {exc}")
                    job.errors.append({"url": url, "error": str(exc)})
                finally:
                    job.processed_urls += 1
                    await job_service.save(job)

        await asyncio.gather(*[process(url) for url in request.urls])

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        await job_service.save(job)
        logger.info(
            f"Job {job.job_id} done — "
            f"{len(job.results)} results, "
            f"{job.cache_hits} cache hits, "
            f"{len(job.errors)} errors"
        )

    # ------------------------------------------------------------------
    # Price comparison across multiple URLs
    # ------------------------------------------------------------------

    async def compare_prices(self, urls: List[str]) -> Dict[str, Any]:
        cache_hits = 0
        results: List[Dict[str, Any]] = []

        async def fetch_one(url: str) -> None:
            nonlocal cache_hits
            cached = await cache_service.get_price(url)
            if cached:
                cache_hits += 1
                results.append({**cached, "from_cache": True})
                return
            req = ScrapeRequest(url=url)
            data = await self.scrape_url(req)
            if data:
                results.append(data)

        await asyncio.gather(*[fetch_one(url) for url in urls])

        priced = sorted(
            [r for r in results if r.get("current_price") is not None],
            key=lambda x: x["current_price"],
        )

        return {
            "comparison": priced,
            "best_price": priced[0] if priced else None,
            "price_range": {
                "min": priced[0]["current_price"] if priced else None,
                "max": priced[-1]["current_price"] if priced else None,
            },
            "total_scraped": len(results),
            "cache_hits": cache_hits,
        }


scraper_service = ScraperService()
