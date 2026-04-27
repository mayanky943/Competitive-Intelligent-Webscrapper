import random
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.scrapers.selectors import USER_AGENTS


class BaseScraper(ABC):
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0

    async def __aenter__(self):
        await self._create_session()
        return self

    async def __aexit__(self, *args):
        await self._close_session()

    async def _create_session(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT),
            follow_redirects=True,
            headers=self._get_base_headers(),
            http2=True,
        )

    async def _close_session(self):
        if self.session:
            await self.session.aclose()

    def _get_base_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

    def _rotate_user_agent(self):
        if self.session:
            self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def fetch(self, url: str) -> Optional[str]:
        if not self.session:
            await self._create_session()

        self._rotate_user_agent()
        self._request_count += 1

        try:
            response = await self.session.get(url)
            response.raise_for_status()
            self._success_count += 1
            logger.debug(f"Fetched {url} [{response.status_code}] ({len(response.text)} bytes)")
            return response.text
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} for {url}")
            self._error_count += 1
            return None
        except Exception as e:
            logger.error(f"Fetch error for {url}: {e}")
            self._error_count += 1
            raise

    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        pass

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "requests": self._request_count,
            "successes": self._success_count,
            "errors": self._error_count,
        }
