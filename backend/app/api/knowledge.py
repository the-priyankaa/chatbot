import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import delete, select

from ..config import settings
from ..core.logging import logger
from ..models import Document, DocumentChunk
from ..schemas.knowledge import DocumentOut, SearchHit, SearchRequest
from ..services.auth import CurrentUser, DbDep
from ..services.embeddings import embed_query, embed_texts, search_chunks

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
SUPPORTED_EXT = {".txt", ".md", ".rst", ".csv", ".json", ".html"}


@router.post("/ingest", response_model=DocumentOut)
async def ingest_document(
    file: UploadFile, user: CurrentUser, db: DbDep
) -> Document:
    filename = Path(file.filename or "document.txt").name
    if Path(filename).suffix.lower() not in SUPPORTED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Supported: {sorted(SUPPORTED_EXT)}",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 2 MB).",
        )
    content = raw.decode("utf-8", errors="replace").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty."
        )

    existing = (
        await db.execute(
            select(Document).where(
                Document.filename == filename, Document.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        # Replace old version
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == existing.id)
        )
        await db.delete(existing)
        await db.flush()

    chunks = _chunk_text(content, settings.kb_chunk_size, settings.kb_chunk_overlap)
    vectors = await embed_texts(chunks)

    doc = Document(user_id=user.id, filename=filename, content=content, chunk_count=len(chunks))
    db.add(doc)
    await db.flush()

    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        db.add(
            DocumentChunk(
                document_id=doc.id,
                index=i,
                content=chunk,
                embedding=vec.tobytes(),
            )
        )
    await db.commit()
    await db.refresh(doc)
    logger.info("ingested doc=%s user=%s chunks=%s", filename, user.id, len(chunks))
    return doc


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(user: CurrentUser, db: DbDep) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, user: CurrentUser, db: DbDep) -> None:
    doc = await db.get(Document, document_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    await db.delete(doc)
    await db.commit()


@router.post("/search", response_model=list[SearchHit])
async def search(payload: SearchRequest, user: CurrentUser, db: DbDep) -> list[SearchHit]:
    query_vec = await embed_query(payload.query)
    hits = await search_chunks(db, query_vec, user.id, payload.top_k)
    return [
        SearchHit(
            document_id=row[0].id,
            filename=row[1],
            chunk_index=row[0].index,
            content=row[0].content,
            score=round(score, 4),
        )
        for row, score in hits
    ]


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        if end < len(normalized):
            # Try to break at a sentence boundary
            boundary = normalized.rfind(". ", start, end)
            if boundary != -1 and boundary > start + size // 2:
                end = boundary + 1
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = end - overlap
    return chunks
