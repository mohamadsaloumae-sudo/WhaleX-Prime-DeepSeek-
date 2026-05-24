import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_guest_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/auth/guest", json={
            "name": "Test User",
            "email": "test@example.com"
        })
    assert response.status_code == 200
    assert "access_token" in response.json()