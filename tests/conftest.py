import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.cache_service import cache_service


@pytest_asyncio.fixture
async def client():
    """HTTP test client with Redis mocked out."""
    with (
        patch.object(cache_service, "connect", new=AsyncMock()),
        patch.object(cache_service, "disconnect", new=AsyncMock()),
        patch.object(cache_service, "ping", new=AsyncMock(return_value=True)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
