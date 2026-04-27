import json
import uuid
from typing import List, Optional

from loguru import logger

from app.models.schemas import JobStatus, ScrapeJob
from app.services.cache_service import cache_service

JOB_TTL = 86400  # jobs live for 24 hours


class JobService:
    async def create(self, urls: List[str]) -> ScrapeJob:
        job = ScrapeJob(
            job_id=str(uuid.uuid4()),
            urls=urls,
            total_urls=len(urls),
            status=JobStatus.PENDING,
        )
        await self._persist(job)
        return job

    async def get(self, job_id: str) -> Optional[ScrapeJob]:
        data = await cache_service.get_job(job_id)
        if data:
            return ScrapeJob.model_validate(data)
        return None

    async def save(self, job: ScrapeJob) -> None:
        await self._persist(job)

    async def list_all(self, limit: int = 20) -> List[ScrapeJob]:
        keys = await cache_service.list_job_keys()
        jobs: List[ScrapeJob] = []
        for key in keys[:limit]:
            job_id = key.split(":")[-1]
            job = await self.get(job_id)
            if job:
                jobs.append(job)
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    async def _persist(self, job: ScrapeJob) -> None:
        await cache_service.set_job(job.job_id, json.loads(job.model_dump_json()), ttl=JOB_TTL)


job_service = JobService()
