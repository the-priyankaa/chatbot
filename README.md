# AI Chatbot

A full-stack, context-aware AI chatbot with conversational history, knowledge
base retrieval (RAG), streaming responses, full JWT authentication, and
feedback analytics.

## Stack

| Layer    | Tech |
|----------|------|
| Backend  | Python 3.12, FastAPI, async SQLAlchemy + SQLite (WAL) |
| AI       | OpenAI GPT via a provider adapter (`app/services/llm.py`) |
| Retrieval| Local embeddings (`fastembed`, all-MiniLM-L6-v2) + numpy cosine search |
| Auth     | Full JWT (access + rotating, revocable refresh tokens), bcrypt |
| Frontend | React 18 + Vite SPA, fetch-based SSE streaming |

## Features

- **Natural language understanding** — intent detection (greeting, knowledge
  query, escalation) and sentiment flagging that adapt the assistant's tone.
- **Conversation management** — persistent per-user histories, topic switching,
  context trimming by token count (`tiktoken`), JSON export.
- **AI integration** — async OpenAI streaming with retry/backoff and graceful
  fallback errors.
- **Knowledge base** — upload `.txt`/`.md` files, chunk + embed locally,
  semantic search, RAG context injection with anti-prompt-injection guards and
  source citations.
- **UX** — typing indicator, streaming tokens, message timestamps, feedback
  ratings (👍/👎 + comments), conversation list with delete/export, KB panel.
- **Security** — bcrypt password hashing, per-user data scoping, input/output
  moderation, rate limiting.
- **Monitoring** — structured request logs, latency capture, per-user stats
  endpoint (`/api/stats`).

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev                # http://localhost:5173 (proxies /api to :8000)
```

For production, `npm run build` in `frontend/` and start the backend with
`SERVE_FRONTEND=true` — FastAPI will serve the built SPA.

## Tests

```bash
cd backend
. .venv/bin/activate
python -m pytest
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account, returns tokens |
| POST | `/api/auth/login` | Login (username or email) |
| POST | `/api/auth/refresh` | Rotate refresh token |
| POST | `/api/auth/logout` | Revoke refresh token |
| GET | `/api/auth/me` | Current user |
| POST | `/api/chat/stream` | Send message, streams SSE events |
| GET | `/api/chat/conversations` | List conversations |
| GET | `/api/chat/conversations/{id}/messages` | Message history |
| GET | `/api/chat/conversations/{id}/export` | Export as JSON |
| DELETE | `/api/chat/conversations/{id}` | Delete conversation |
| POST | `/api/knowledge/ingest` | Upload a document (multipart) |
| GET | `/api/knowledge/documents` | List uploaded documents |
| POST | `/api/knowledge/search` | Semantic search |
| POST | `/api/feedback?message_id=...` | Rate a response (1 or 2) |
| GET | `/api/stats` | Engagement / satisfaction stats |

## SSE event stream

`POST /api/chat/stream` returns `text/event-stream` with named events:
`start` (conversation id), `sources` (retrieved KB sources), `token`
(incremental response text), `done`, and `error`.

## Security notes

- Never commit `.env`; generate a strong `JWT_SECRET`.
- Embeddings and all data are stored locally; the only external call is the
  OpenAI API using `OPENAI_API_KEY`.
- Retrieved KB content is delimited and the model is instructed to ignore any
  instructions inside it.
