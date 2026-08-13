import json
import time
from collections.abc import AsyncGenerator, AsyncIterable, Iterable

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from ..config import settings
from ..core.logging import logger
from ..core.ratelimit import limiter
from ..core.security import utcnow
from ..models import Conversation, Message
from ..schemas.chat import (
    ChatRequest,
    ConversationCreate,
    ConversationOut,
    MessageOut,
)
from ..schemas.knowledge import SearchHit
from ..services.auth import CurrentUser, DbDep
from ..services.llm import get_provider, trim_history
from ..services.moderation import moderate_input, moderate_output
from ..services.nlu import detect_intent, detect_sentiment
from ..services.rag import build_kb_instruction, retrieve_context

router = APIRouter(prefix="/chat", tags=["chat"])

_RATE = f"{settings.rate_limit_per_minute}/minute"


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(user: CurrentUser, db: DbDep) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    payload: ConversationCreate, user: CurrentUser, db: DbDep
) -> Conversation:
    conv = Conversation(
        user_id=user.id, title=payload.title or "New chat"
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str, user: CurrentUser, db: DbDep
) -> None:
    conv = await _get_owned_conversation(db, user.id, conversation_id)
    await db.delete(conv)
    await db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: str, user: CurrentUser, db: DbDep
) -> list[Message]:
    await _get_owned_conversation(db, user.id, conversation_id)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str, user: CurrentUser, db: DbDep
) -> dict:
    conv = await _get_owned_conversation(db, user.id, conversation_id)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = list((await db.execute(stmt)).scalars().all())
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "exported_at": utcnow().isoformat(),
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/stream")
@limiter.limit(_RATE)
async def stream_chat(request: Request, payload: ChatRequest, user: CurrentUser, db: DbDep):
    blocked = moderate_input(payload.message)
    if blocked:
        return StreamingResponse(
            _sse([{"type": "error", "data": json.dumps({"text": blocked})}]),
            media_type="text/event-stream",
        )

    conv_id = payload.conversation_id
    conv: Conversation | None = None
    if conv_id:
        conv = await _get_owned_conversation(db, user.id, conv_id)
    else:
        conv = Conversation(user_id=user.id, title=payload.title or payload.message[:40])
        db.add(conv)
        await db.flush()

    user_msg = Message(conversation_id=conv.id, role="user", content=payload.message)
    db.add(user_msg)
    await db.commit()

    generator = _stream_llm_response(db, conv, user_msg, user.id)
    return StreamingResponse(_sse(generator), media_type="text/event-stream")


async def _stream_llm_response(
    db, conv: Conversation, user_msg: Message, user_id: str
) -> AsyncGenerator[dict, None]:
    start = time.perf_counter()

    stmt = (
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )
    history = list((await db.execute(stmt)).scalars().all())
    history = history[-settings.max_history_messages :]

    # Retrieve KB context for grounding (skip for greetings)
    context: list[SearchHit] = []
    intent = detect_intent(user_msg.content)
    sentiment = detect_sentiment(user_msg.content)
    if intent != "greeting":
        try:
            context = await retrieve_context(db, user_msg.content, user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("KB retrieval failed: %s", exc)

    system_prompt = settings.llm_system_prompt
    kb_instruction = build_kb_instruction(context)
    if kb_instruction:
        system_prompt = f"{system_prompt}\n\n{kb_instruction}"
    if intent == "escalation":
        system_prompt += (
            "\n\nThe user wants a human agent. Acknowledge this, apologize for the "
            "inconvenience, and provide the support contact process."
        )
    if sentiment == "negative":
        system_prompt += "\n\nThe user seems frustrated. Be extra empathetic and concise."

    llm_messages = trim_history(
        system_prompt,
        [
            {"role": m.role if m.role != "assistant" else "assistant", "content": m.content}
            for m in history[:-1]
        ],
        settings.context_window_tokens,
    )
    llm_messages.append({"role": "user", "content": user_msg.content})

    yield {"type": "start", "data": json.dumps({"conversation_id": conv.id})}
    if context:
        yield {
            "type": "sources",
            "data": json.dumps(
                [{"filename": c["filename"], "score": c["score"]} for c in context]
            ),
        }

    buffer: list[str] = []
    stream_error: str | None = None
    completed_normally = False
    assistant_msg: Message | None = None
    try:
        try:
            provider = get_provider()
            async for delta in provider.stream(llm_messages):
                buffer.append(delta)
                yield {"type": "token", "data": json.dumps({"text": delta})}
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM stream error")
            stream_error = (
                "Sorry, the AI service is unavailable right now. Please try again."
            )
            yield {
                "type": "error",
                "data": json.dumps({"text": stream_error}),
            }

        content = stream_error or moderate_output("".join(buffer))
        if content:
            assistant_msg = await _persist_assistant_reply(db, conv, user_msg, content)
        completed_normally = True
    finally:
        # Client disconnected mid-stream (GeneratorExit): persist whatever we have
        # so the partial reply and conversation title are not lost.
        if not completed_normally and (buffer or stream_error):
            content = stream_error or moderate_output("".join(buffer))
            if content:
                try:
                    assistant_msg = await _persist_assistant_reply(
                        db, conv, user_msg, content
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to persist partial reply")

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "chat complete user=%s conv=%s intent=%s sentiment=%s kb_hits=%s latency_ms=%s",
        user_id,
        conv.id,
        intent,
        sentiment,
        len(context),
        latency_ms,
    )
    yield {
        "type": "done",
        "data": json.dumps(
            {
                "latency_ms": latency_ms,
                "message_id": assistant_msg.id if assistant_msg else None,
            }
        ),
    }


async def _persist_assistant_reply(
    db, conv: Conversation, user_msg: Message, content: str
) -> Message:
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=content)
    db.add(assistant_msg)
    title_text = " ".join(user_msg.content.split())
    conv.title = (
        conv.title if conv.title and conv.title != "New chat" else title_text[:40]
    )
    conv.updated_at = utcnow()
    await db.commit()
    return assistant_msg


async def _get_owned_conversation(
    db, user_id: str, conversation_id: str
) -> Conversation:
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conv


async def _sse(
    events: Iterable[dict] | AsyncIterable[dict],
) -> AsyncGenerator[str, None]:
    if isinstance(events, AsyncIterable):
        async for event in events:
            yield f"event: {event['type']}\ndata: {event.get('data') or ''}\n\n"
    else:
        for event in events:
            yield f"event: {event['type']}\ndata: {event.get('data') or ''}\n\n"
