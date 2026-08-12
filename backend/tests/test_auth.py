import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    res = await client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"},
    )
    assert res.status_code == 201
    assert res.json()["access_token"]

    res = await client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "password123"},
    )
    assert res.status_code == 200
    assert res.json()["refresh_token"]

    res = await client.post(
        "/api/auth/login",
        json={"identifier": "alice@example.com", "password": "wrongpass"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    payload = {
        "username": "bob",
        "email": "bob@example.com",
        "password": "password123",
    }
    assert (await client.post("/api/auth/register", json=payload)).status_code == 201
    res = await client.post(
        "/api/auth/register",
        json={**payload, "email": "bob2@example.com"},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_me_and_protected_route(client):
    assert (await client.get("/api/auth/me")).status_code == 401
    res = await client.post(
        "/api/auth/register",
        json={"username": "carol", "email": "carol@example.com", "password": "password123"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "carol"


@pytest.mark.asyncio
async def test_refresh_rotation_and_revocation(client):
    res = await client.post(
        "/api/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "password123"},
    )
    tokens = res.json()
    refresh = tokens["refresh_token"]

    res = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 200
    new_refresh = res.json()["refresh_token"]

    # Old refresh token must be rejected after rotation
    res = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 401

    res = await client.post("/api/auth/logout", json={"refresh_token": new_refresh})
    assert res.status_code == 204

    res = await client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_rotation_single_session(client):
    res = await client.post(
        "/api/auth/register",
        json={"username": "erin", "email": "erin@example.com", "password": "password123"},
    )
    first_refresh = res.json()["refresh_token"]

    res = await client.post(
        "/api/auth/login",
        json={"identifier": "erin", "password": "password123"},
    )
    assert res.status_code == 200
    second_refresh = res.json()["refresh_token"]

    # First session token revoked by rotation on second login
    res = await client.post("/api/auth/refresh", json={"refresh_token": first_refresh})
    assert res.status_code == 401
    res = await client.post("/api/auth/refresh", json={"refresh_token": second_refresh})
    assert res.status_code == 200
