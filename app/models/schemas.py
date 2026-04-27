import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScraperType(str, Enum):
    BASIC = "basic"
    DYNAMIC = "dynamic"
    CUSTOM = "custom"


class PriceData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str
    product_name: Optional[str] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "USD"
    discount_percentage: Optional[float] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    seller: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScrapeRequest(BaseModel):
    url: str
    scraper_type: ScraperType = ScraperType.BASIC
    custom_selectors: Optional[Dict[str, List[str]]] = None
    use_cache: bool = True
    force_refresh: bool = False
    timeout: Optional[int] = None


class BatchScrapeRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, max_length=50)
    scraper_type: ScraperType = ScraperType.BASIC
    custom_selectors: Optional[Dict[str, List[str]]] = None
    use_cache: bool = True
    force_refresh: bool = False
    concurrent_limit: int = Field(default=5, ge=1, le=20)


class ScrapeJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    urls: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: List[PriceData] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    total_urls: int = 0
    processed_urls: int = 0


class CacheStats(BaseModel):
    total_keys: int
    hits: int
    misses: int
    hit_rate_percentage: float
    memory_used_mb: float
    evicted_keys: int
    uptime_seconds: int


class PriceComparison(BaseModel):
    comparison: List[Dict[str, Any]]
    best_price: Optional[Dict[str, Any]]
    price_range: Dict[str, Optional[float]]
    total_scraped: int
    cache_hits: int


class HealthStatus(BaseModel):
    status: str
    redis_connected: bool
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
