import json

import pytest


@pytest.mark.asyncio
async def test_conversation_crud_and_isolation(auth_client, second_user):
    res = await auth_client.post("/api/chat/conversations", json={"title": "Hello world"})
    assert res.status_code == 200
    conv_id = res.json()["id"]

    res = await auth_client.get("/api/chat/conversations")
    assert len(res.json()) == 1

    # Other user must not see it
    res = await client_headers(auth_client, second_user["access_token"]).get(
        "/api/chat/conversations"
    )
    assert res.json() == []


@pytest.mark.asyncio
async def test_delete_and_export(auth_client):
    res = await auth_client.post("/api/chat/conversations", json={"title": "Export me"})
    conv_id = res.json()["id"]

    res = await auth_client.get(f"/api/chat/conversations/{conv_id}/export")
    assert res.status_code == 200
    assert res.json()["title"] == "Export me"
    assert res.json()["messages"] == []

    res = await auth_client.delete(f"/api/chat/conversations/{conv_id}")
    assert res.status_code == 204
    res = await auth_client.get("/api/chat/conversations")
    assert res.json() == []


@pytest.mark.asyncio
async def test_stream_moderation_block(auth_client):
    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "hello", "title": "hi"},
    )
    assert res.status_code == 200
    body = res.text
    # No API key set in test env -> expect graceful error event, not crash
    assert "event:" in body
    assert "done" in body or "error" in body


@pytest.mark.asyncio
async def test_stream_without_api_key_returns_error_event(auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")
    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "what is the weather?", "title": "hi"},
    )
    assert res.status_code == 200
    events = [e for e in res.text.split("event:") if e.strip()]
    types = [e.split("\n")[0].strip() for e in events]
    assert "error" in types


@pytest.mark.asyncio
async def test_feedback_and_stats(auth_client):
    res = await auth_client.post("/api/chat/conversations", json={})
    conv_id = res.json()["id"]

    # craft a message row directly for feedback testing via stream (no API key -> error)
    res = await auth_client.post(
        "/api/chat/stream",
        json={"conversation_id": conv_id, "message": "hi"},
    )
    assert res.status_code == 200

    msgs = (await auth_client.get(f"/api/chat/conversations/{conv_id}/messages")).json()
    assistant = next((m for m in msgs if m["role"] == "assistant"), None)
    assert assistant is not None

    res = await auth_client.post(f"/api/feedback?message_id={assistant['id']}", json={"rating": 2})
    assert res.status_code == 201

    stats = (await auth_client.get("/api/stats")).json()
    assert stats["feedback_count"] == 1
    assert stats["satisfaction_percent"] == 100.0


def client_headers(client, token):
    class Wrapper:
        def __init__(self, c, t):
            self._c = c
            self._t = t

        async def get(self, url):
            return await self._c.get(url, headers={"Authorization": f"Bearer {self._t}"})

    return Wrapper(client, token)
