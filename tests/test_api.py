import pytest
from unittest.mock import AsyncMock, patch

from app.models.schemas import JobStatus, ScrapeJob


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["redis_connected"] is True
    assert body["status"] == "healthy"


# ------------------------------------------------------------------
# Single scrape
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_single_success(client):
    mock_result = {
        "url": "https://example.com/product",
        "product_name": "Widget Pro",
        "current_price": 29.99,
        "currency": "USD",
        "from_cache": False,
    }
    with patch(
        "app.api.routes.scrape.scraper_service.scrape_url",
        new=AsyncMock(return_value=mock_result),
    ):
        response = await client.post("/api/v1/scrape/", json={"url": "https://example.com/product"})
    assert response.status_code == 200
    assert response.json()["current_price"] == 29.99


@pytest.mark.asyncio
async def test_scrape_single_no_data_returns_422(client):
    with patch(
        "app.api.routes.scrape.scraper_service.scrape_url",
        new=AsyncMock(return_value=None),
    ):
        response = await client.post("/api/v1/scrape/", json={"url": "https://example.com/404"})
    assert response.status_code == 422


# ------------------------------------------------------------------
# Batch scrape
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_batch_returns_202_job(client):
    with patch(
        "app.api.routes.scrape.scraper_service.run_batch_job",
        new=AsyncMock(),
    ), patch(
        "app.api.routes.scrape.job_service.create",
        new=AsyncMock(
            return_value=ScrapeJob(
                urls=["https://a.com", "https://b.com"],
                total_urls=2,
                status=JobStatus.PENDING,
            )
        ),
    ):
        response = await client.post(
            "/api/v1/scrape/batch",
            json={"urls": ["https://a.com", "https://b.com"]},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["total_urls"] == 2


# ------------------------------------------------------------------
# Job polling
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_not_found(client):
    with patch(
        "app.api.routes.scrape.job_service.get",
        new=AsyncMock(return_value=None),
    ):
        response = await client.get("/api/v1/scrape/jobs/nonexistent-id")
    assert response.status_code == 404


# ------------------------------------------------------------------
# Cache stats
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_stats(client):
    mock_stats = {
        "total_keys": 50,
        "hits": 200,
        "misses": 50,
        "hit_rate_percentage": 80.0,
        "memory_used_mb": 2.1,
        "evicted_keys": 0,
        "uptime_seconds": 7200,
    }
    with patch(
        "app.api.routes.cache.cache_service.get_stats",
        new=AsyncMock(return_value=mock_stats),
    ):
        response = await client.get("/api/v1/cache/stats")
    assert response.status_code == 200
    assert response.json()["hit_rate_percentage"] == 80.0


# ------------------------------------------------------------------
# Price comparison
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compare_prices(client):
    mock_comparison = {
        "comparison": [
            {"url": "https://a.com", "current_price": 19.99, "currency": "USD"},
            {"url": "https://b.com", "current_price": 24.99, "currency": "USD"},
        ],
        "best_price": {"url": "https://a.com", "current_price": 19.99, "currency": "USD"},
        "price_range": {"min": 19.99, "max": 24.99},
        "total_scraped": 2,
        "cache_hits": 1,
    }
    with patch(
        "app.api.routes.scrape.scraper_service.compare_prices",
        new=AsyncMock(return_value=mock_comparison),
    ):
        response = await client.post(
            "/api/v1/scrape/compare",
            json={"urls": ["https://a.com", "https://b.com"]},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["best_price"]["current_price"] == 19.99
    assert body["price_range"]["min"] == 19.99
