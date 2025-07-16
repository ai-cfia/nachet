import pytest
from app import app

@pytest.mark.asyncio
async def test_health():
    test = app.test_client()
    response = await test.get('/health')
    assert response.status_code == 200
