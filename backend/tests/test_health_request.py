import pytest

# from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as ac:
        # test = TestClient(app)
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
