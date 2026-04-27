from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthStatus
from app.services.cache_service import cache_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus, summary="Application health check")
async def health_check():
    redis_ok = await cache_service.ping()
    return HealthStatus(
        status="healthy" if redis_ok else "degraded",
        redis_connected=redis_ok,
        version=settings.APP_VERSION,
    )
