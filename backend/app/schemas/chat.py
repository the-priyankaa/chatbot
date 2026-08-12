from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = ...  # noqa: A003
    title: str | None = None


class StreamEvent(BaseModel):
    type: str  # start | token | done | error | sources
    data: str | list[dict] | None = None
