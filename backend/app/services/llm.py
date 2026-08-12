import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from ..config import settings
from ..core.logging import logger

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5


@dataclass
class LLMResponse:
    content: str = ""
    sources: list[dict] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict]) -> str:
        ...

    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        ...


class _OpenAICompatibleProvider(LLMProvider):
    """Shared streaming/retry logic for OpenAI-compatible APIs."""

    client: AsyncOpenAI

    def _build(self, messages: list[dict]) -> dict:
        raise NotImplementedError

    async def _with_retry(self, factory):
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await factory()
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning("LLM call failed (attempt %s): %s", attempt + 1, exc)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF * (2**attempt))
        raise last_err  # type: ignore[misc]

    async def complete(self, messages: list[dict]) -> str:
        async def call() -> str:
            resp = await self.client.chat.completions.create(**self._build(messages))
            return resp.choices[0].message.content or ""

        return await self._with_retry(call)

    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                stream = await self.client.chat.completions.create(
                    **self._build(messages), stream=True
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
                return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning("LLM stream failed (attempt %s): %s", attempt + 1, exc)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF * (2**attempt))
        raise last_err  # type: ignore[misc]


class OpenAIProvider(_OpenAICompatibleProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set; OpenAI provider disabled")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key or "sk-dummy")

    def _build(self, messages: list[dict]) -> dict:
        return {
            "model": settings.openai_model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }


class OllamaProvider(_OpenAICompatibleProvider):
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key="ollama", base_url=settings.llm_ollama_base_url
        )
        logger.info(
            "Using local Ollama model %s at %s",
            settings.llm_ollama_model,
            settings.llm_ollama_base_url,
        )

    def _build(self, messages: list[dict]) -> dict:
        return {
            "model": settings.llm_ollama_model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }


class FallbackProvider(LLMProvider):
    """Tries each provider in order; falls back on request-time failures."""

    def __init__(self, providers: list[LLMProvider]) -> None:
        self.providers = [p for p in providers if p is not None]
        if not self.providers:
            raise ValueError("At least one LLM provider is required")

    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        last_err: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                async for delta in provider.stream(messages):
                    yield delta
                return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning(
                    "Provider %s failed (%s), %s",
                    provider.__class__.__name__,
                    exc,
                    "trying next" if i < len(self.providers) - 1 else "no more providers",
                )
        raise last_err  # type: ignore[misc]

    async def complete(self, messages: list[dict]) -> str:
        last_err: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                return await provider.complete(messages)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning(
                    "Provider %s failed (%s), %s",
                    provider.__class__.__name__,
                    exc,
                    "trying next" if i < len(self.providers) - 1 else "no more providers",
                )
        raise last_err  # type: ignore[misc]


def get_provider() -> LLMProvider:
    providers: list[LLMProvider] = []
    if settings.openai_api_key:
        providers.append(OpenAIProvider())
    providers.append(OllamaProvider())
    return FallbackProvider(providers)


# ---- token counting / history trimming ----

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        import tiktoken

        _encoder = tiktoken.encoding_for_model(settings.openai_model)
    return _encoder


def count_tokens(text: str) -> int:
    try:
        return len(_get_encoder().encode(text))
    except Exception:  # noqa: BLE001
        return len(text) // 4


def trim_history(
    system_prompt: str, history: list[dict], max_tokens: int
) -> list[dict]:
    budget = max_tokens - count_tokens(system_prompt)
    if budget <= 0:
        return [{"role": "system", "content": system_prompt}]

    selected: list[dict] = []
    used = 0
    for msg in reversed(history[-settings.max_history_messages:]):
        cost = count_tokens(msg.get("content", "")) + 8
        if used + cost > budget and selected:
            break
        used += cost
        selected.append(msg)
    selected.reverse()

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(selected)
    return messages
