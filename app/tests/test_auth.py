import pytest

async def test_register_and_login(client):
    # register
    r = await client.post("/auth/register", json={"email": "test@example.com", "password": "secret123"})
    assert r.status_code == 201

    # login
    r2 = await client.post("/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert r2.status_code == 200
    data = r2.json()
    assert "access_token" in data and "refresh_token" in data
