import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_chatbot.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["SERVE_FRONTEND"] = "false"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import Base, engine


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(autouse=True)
def fast_llm_retries():
    import app.services.llm as llm

    llm.MAX_RETRIES = 1
    yield
    llm.MAX_RETRIES = 3


@pytest_asyncio.fixture(autouse=True)
def stub_llm(monkeypatch):
    """Keep stream tests hermetic: fail fast instead of hitting real providers
    (api.openai.com or a local Ollama), which makes results network-dependent."""
    from app.services.llm import LLMProvider

    class _FailingLLM(LLMProvider):
        async def complete(self, messages):
            raise RuntimeError("stub")

        async def stream(self, messages):
            if False:  # pragma: no cover - makes this an async generator
                yield None
            raise RuntimeError("stub")

    monkeypatch.setattr("app.api.chat.get_provider", lambda: _FailingLLM())
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client):
    res = await client.post(
        "/api/auth/register",
        json={
            "username": "tester",
            "email": "tester@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 201, res.text
    tokens = res.json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    client.private_tokens = tokens
    return client


@pytest_asyncio.fixture
async def second_user(client):
    res = await client.post(
        "/api/auth/register",
        json={
            "username": "other",
            "email": "other@example.com",
            "password": "password456",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()
