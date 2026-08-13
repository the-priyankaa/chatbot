import asyncio

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.logging import logger

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding

        logger.info("Loading embedding model %s ...", settings.embeddings_model)
        _embedder = TextEmbedding(model_name=settings.embeddings_model)
    return _embedder


async def embed_texts(texts: list[str]) -> list[np.ndarray]:
    def _run() -> list[np.ndarray]:
        model = get_embedder()
        return [np.asarray(v, dtype="float32") for v in model.embed(texts)]

    return await asyncio.to_thread(_run)


async def embed_query(text: str) -> np.ndarray:
    (vec,) = await embed_texts([text])
    return vec


def cosine_similarity(query: np.ndarray, vectors: list[np.ndarray]) -> np.ndarray:
    if not vectors:
        return np.array([], dtype="float32")
    mat = np.stack(vectors)
    query = query / (np.linalg.norm(query) + 1e-12)
    mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12)
    return (mat @ query).astype("float32")


async def search_chunks(
    db: AsyncSession, query_vec: np.ndarray, user_id: str, top_k: int
) -> list[tuple[object, float]]:
    from ..models import Document, DocumentChunk

    stmt = (
        select(DocumentChunk, Document.filename, Document.id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == user_id)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    def _compute() -> list[tuple[object, float]]:
        query_dim = len(query_vec)
        normalized: list[np.ndarray] = []
        for row in rows:
            try:
                vec = np.frombuffer(row[0].embedding, dtype="float32")
            except Exception:  # noqa: BLE001
                vec = np.zeros(query_dim, dtype="float32")
            if vec.size != query_dim:
                if vec.size > query_dim:
                    vec = vec[:query_dim]
                else:
                    padded = np.zeros(query_dim, dtype="float32")
                    padded[: vec.size] = vec
                    vec = padded
            normalized.append(vec)
        scores = cosine_similarity(query_vec, normalized)
        return list(zip(rows, scores.tolist()))

    scored = await asyncio.to_thread(_compute)
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]