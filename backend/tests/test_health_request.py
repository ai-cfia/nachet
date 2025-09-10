import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.asyncio
async def test_health():
    test = TestClient(app)
    response = await test.get('/health')
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
