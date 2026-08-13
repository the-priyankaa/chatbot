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
async def test_stream_toxic_block_returns_json_error(auth_client):
    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "I will kill you", "title": "block"},
    )
    assert res.status_code == 200
    body = res.text
    assert "event: error" in body
    assert '"text"' in body
    assert "I can't help" in body


@pytest.mark.asyncio
async def test_done_event_includes_message_id(auth_client):
    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "hi", "title": "msg-id"},
    )
    assert res.status_code == 200
    done_block = res.text.split("event: done")[1].split("\n\n")[0]
    assert '"message_id"' in done_block


@pytest.mark.asyncio
async def test_stream_empty_message_rejected(auth_client):
    res = await auth_client.post("/api/chat/stream", json={"message": ""})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_admin_stats_requires_auth(client):
    assert (await client.get("/api/admin/stats")).status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_with_auth(auth_client):
    res = await auth_client.get("/api/admin/stats")
    assert res.status_code == 200
    assert "users" in res.json()


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


def _conv_id_from_stream(body: str) -> str:
    import json

    for line in body.splitlines():
        if line.startswith("data:") and '"conversation_id"' in line:
            return json.loads(line[5:].strip())["conversation_id"]
    raise AssertionError("no start event with conversation_id in stream body")


@pytest.mark.asyncio
async def test_llm_failure_persists_nonempty_assistant_message(auth_client):
    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "hello", "title": "err"},
    )
    assert res.status_code == 200
    conv_id = _conv_id_from_stream(res.text)
    msgs = (
        await auth_client.get(f"/api/chat/conversations/{conv_id}/messages")
    ).json()
    assistant = next((m for m in msgs if m["role"] == "assistant"), None)
    assert assistant is not None
    assert assistant["content"]  # error text persisted, not an empty bubble


@pytest.mark.asyncio
async def test_stream_skips_kb_retrieval_for_greeting(auth_client, monkeypatch):
    import app.api.chat as chat_module

    calls = {"count": 0}

    async def fake_retrieve(db, query, user_id, top_k=None):
        calls["count"] += 1
        return []

    monkeypatch.setattr(chat_module, "retrieve_context", fake_retrieve)

    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "hello there", "title": "greet"},
    )
    assert res.status_code == 200
    assert calls["count"] == 0

    res = await auth_client.post(
        "/api/chat/stream",
        json={"message": "what is the weather?", "title": "ask"},
    )
    assert res.status_code == 200
    assert calls["count"] == 1


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
