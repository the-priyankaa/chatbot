from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    chunk_count: int
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    content: str
    score: float


class FeedbackCreate(BaseModel):
    rating: int = ...  # noqa: A003  # 1 or 2
    comment: str | None = None
