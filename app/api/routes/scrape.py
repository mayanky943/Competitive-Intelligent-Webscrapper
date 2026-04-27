from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query

from app.models.schemas import (
    BatchScrapeRequest,
    PriceComparison,
    ScrapeJob,
    ScrapeRequest,
)
from app.services.job_service import job_service
from app.services.scraper_service import scraper_service

router = APIRouter(prefix="/scrape", tags=["scraping"])


@router.post(
    "/",
    summary="Scrape a single product URL",
    response_description="Extracted pricing data (from_cache=true when served from Redis)",
)
async def scrape_single(request: ScrapeRequest) -> Dict[str, Any]:
    result = await scraper_service.scrape_url(request)
    if not result:
        raise HTTPException(status_code=422, detail="Could not extract pricing data from the URL")
    return result


@router.post(
    "/batch",
    response_model=ScrapeJob,
    status_code=202,
    summary="Submit a batch scrape job (async)",
    response_description="Job created — poll /scrape/jobs/{job_id} for results",
)
async def scrape_batch(
    request: BatchScrapeRequest,
    background_tasks: BackgroundTasks,
) -> ScrapeJob:
    job = await job_service.create(request.urls)
    background_tasks.add_task(scraper_service.run_batch_job, job, request)
    return job


@router.get(
    "/jobs/{job_id}",
    response_model=ScrapeJob,
    summary="Poll a batch job for status and results",
)
async def get_job(job_id: str) -> ScrapeJob:
    job = await job_service.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get(
    "/jobs",
    response_model=List[ScrapeJob],
    summary="List recent scrape jobs",
)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="Max jobs to return"),
) -> List[ScrapeJob]:
    return await job_service.list_all(limit=limit)


@router.post(
    "/compare",
    response_model=PriceComparison,
    summary="Scrape and compare prices across multiple URLs",
    response_description="Results sorted by price (cheapest first)",
)
async def compare_prices(
    urls: List[str] = Body(..., min_length=2, max_length=20, embed=True),
) -> PriceComparison:
    result = await scraper_service.compare_prices(urls)
    if not result["comparison"]:
        raise HTTPException(status_code=422, detail="No pricing data found for provided URLs")
    return PriceComparison(**result)


@router.delete(
    "/cache/{url:path}",
    summary="Invalidate cached price for a specific URL",
)
async def invalidate_cache(url: str):
    from app.services.cache_service import cache_service

    deleted = await cache_service.delete_price(url)
    return {"url": url, "invalidated": deleted}
