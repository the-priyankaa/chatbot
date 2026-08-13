import numpy as np
import pytest

from app.api.knowledge import _chunk_text
from app.services.embeddings import cosine_similarity
from app.services.moderation import is_toxic, moderate_input, moderate_output
from app.services.nlu import detect_intent, detect_sentiment


@pytest.mark.asyncio
async def test_search_top_k_rejected(auth_client):
    res = await auth_client.post(
        "/api/knowledge/search", json={"query": "x", "top_k": 500}
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_search_handles_embedding_dimension_mismatch(auth_client):
    import numpy as np
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import Document, DocumentChunk, User
    from app.services.embeddings import search_chunks

    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.username == "tester"))
        ).scalar_one()
        doc = Document(
            user_id=user.id, filename="old.txt", content="old model", chunk_count=1
        )
        db.add(doc)
        await db.flush()
        db.add(
            DocumentChunk(
                document_id=doc.id,
                index=0,
                content="legacy chunk",
                embedding=np.array([1.0, 2.0, 3.0], dtype="float32").tobytes(),
            )
        )
        await db.commit()

        longer = np.array([1.0, 2.0, 3.0, 4.0], dtype="float32")
        hits = await search_chunks(db, longer, user.id, 4)
        assert isinstance(hits, list)
        assert hits[0][1] >= -1.0

        shorter = np.array([1.0, 2.0], dtype="float32")
        hits = await search_chunks(db, shorter, user.id, 4)
        assert isinstance(hits, list)
        assert hits[0][1] >= -1.0


class TestChunking:
    def test_short_text_single_chunk(self):
        assert _chunk_text("hello world", 700, 80) == ["hello world"]

    def test_long_text_breaks_and_overlaps(self):
        text = " ".join(["word%d." % i for i in range(200)])
        chunks = _chunk_text(text, 100, 20)
        assert len(chunks) > 1
        assert all(chunks)
        assert "".join(chunks)[:30] == text[:30]

    def test_whitespace_normalized(self):
        assert _chunk_text("a\n\n\n  b", 700, 80) == ["a b"]


class TestCosineSimilarity:
    def test_perfect_match(self):
        v = np.array([1.0, 0.0, 0.0], dtype="float32")
        assert cosine_similarity(v, [v])[0] == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal(self):
        v1 = np.array([1.0, 0.0], dtype="float32")
        v2 = np.array([0.0, 1.0], dtype="float32")
        assert cosine_similarity(v1, [v2])[0] == pytest.approx(0.0, abs=1e-5)

    def test_empty(self):
        assert cosine_similarity(np.array([1.0]), []).size == 0


class TestNlu:
    def test_intent_greeting(self):
        assert detect_intent("hello there") == "greeting"

    def test_intent_escalation(self):
        assert detect_intent("I need a human agent please") == "escalation"

    def test_intent_knowledge(self):
        assert detect_intent("what do your FAQ documents say about refunds") == "knowledge_query"

    def test_intent_general(self):
        assert detect_intent("how do stars form?") == "general"

    def test_sentiment_negative(self):
        assert detect_sentiment("this is absolutely terrible") == "negative"

    def test_sentiment_neutral(self):
        assert detect_sentiment("could you explain that again?") == "neutral"


class TestModeration:
    def test_is_toxic(self):
        assert is_toxic("you are such an idiot")
        assert not is_toxic("I appreciate your help")

    def test_moderate_input_blocks_toxic(self):
        assert moderate_input("go away you dumbass") is not None

    def test_moderate_input_length(self):
        assert moderate_input("x" * 5000) is not None

    def test_moderate_input_allows_clean(self):
        assert moderate_input("What is your name?") is None

    def test_moderate_output_filters_toxic(self):
        assert "help with that" in moderate_output("you are an idiot")
