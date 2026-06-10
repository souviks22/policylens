# PolicyLens

**AI-powered policy document comparison with semantic analysis, RAG grounding, and streaming chat.**

PolicyLens is a full-stack application that takes two policy PDFs, runs a multi-stage analysis pipeline (text diff → RAG retrieval → GPT-4o semantic analysis → embedding-based section alignment), and surfaces a rich interactive dashboard with per-change impact scoring, a similarity heatmap, inline annotations, and a streaming chat interface grounded in the comparison context.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            BROWSER (Next.js 14)                          │
│                                                                          │
│  ┌─────────────┐  ┌──────────────────────────────────────────────────┐   │
│  │  Auth Pages │  │             Comparison Dashboard                 │   │
│  │  /login     │  │  FileDropZone → AnalyzingOverlay → Results       │   │
│  │  AuthContext│  │                                                  │   │
│  │  JWT Bearer │  │  ┌──────────────┐  ┌────────────────────────┐    │   │
│  └─────────────┘  │  │ SemanticChgs │  │    SectionAnalysis     │    │   │
│                   │  │ DiffViewer   │  │   SimilarityMatrix     │    │   │
│  ┌─────────────┐  │  │ ExecutiveSumm│  │   ComparisonChat (SSE) │    │   │
│  │  History    │  │  │ Annotations  │  │   RagContextPanel      │    │   │
│  │  /history   │  │  └──────────────┘  └────────────────────────┘    │   │ 
│  └─────────────┘  └──────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    Knowledge Base  /knowledge-base                 │  │
│  │            Upload PDFs/TXT  ·  Global & Personal scopes            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ HTTP / SSE  (Axios, JWT Bearer)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                          FastAPI  (Python 3.12)                           │
│                                                                           │
│  POST /api/auth/register|login   GET /api/auth/me                         │
│  POST /api/documents/upload      GET /api/documents/{id}                  │
│                                                                           │
│  POST /api/comparison/analyze  ──────────────────────────────────────┐    │
│    │                                                                 │    │
│    │  Step 1: TextDiffService                                        │    │
│    │    difflib paragraph-level diff → DiffChunk[]                   │    │
│    │    word-level inline diff for modified blocks                   │    │
│    │                                                                 │    │
│    │  Step 2: RAGService  (best-effort, non-blocking)                │    │
│    │    Query ChromaDB  →  global_kb  +  user_kb_{uid}               │    │
│    │    Score-threshold filter  →  format_context_for_prompt()       │    │
│    │                                                                 │    │
│    │  Step 3: SemanticAnalyzer  (GPT-4o)                             │    │
│    │    Diff description + RAG context → SemanticChange[]            │    │
│    │    Fields: change_type, impact_level, compliance_impact,        │    │
│    │            regulatory_impact, recommendations                   │    │
│    │                                                                 │    │
│    │  Step 4: Executive Summary  (GPT-4o)                            │    │
│    │    Aggregated changes + RAG context → ComparisonSummary         │    │
│    │    Fields: key_changes, risk_areas, compliance_flags            │    │
│    │                                                                 │    │
│    │  Step 5: SectionAligner  (EmbeddingService)                     │    │
│    │    Heading extraction + batched embeddings                      │    │
│    │    Cosine similarity matrix → SectionMatch[]                    │    │
│    │    Detects: unchanged / modified / added / deleted / clones     │    │
│    │                                                                 │    │
│    └──→  ComparisonResult  persisted to SQLite / Postgres  ──────────┘    │
│                                                                           │
│  GET  /api/comparison/{id}       DELETE /api/comparison/{id}              │
│  GET  /api/comparison/history                                             │
│                                                                           │
│  POST /api/chat/{comparison_id}  ──  SSE stream                           │
│    ChatService builds grounded system prompt from ComparisonResult        │
│    Streams GPT-4o tokens as text/event-stream                             │
│                                                                           │
│  POST /api/kb/upload             GET  /api/kb/documents                   │
│  DELETE /api/kb/documents/{id}   GET  /api/kb/search                      │
│  GET  /api/kb/stats                                                       │
│                                                                           │
│  POST /api/annotations/          PATCH /api/annotations/{id}/resolve      │
│  DELETE /api/annotations/{id}                                             │
│                                                                           │
│  GET  /api/export/{id}/pdf       GET  /api/export/{id}/docx               │
│    ReportLab (PDF)  ·  python-docx (DOCX)                                 │
└───────────────────┬──────────────────────────┬────────────────────────────┘
                    │                          │
        ┌───────────▼─────────┐    ┌───────────▼────────────┐
        │  SQLite / Postgres  │    │       ChromaDB         │
        │  (SQLAlchemy async) │    │  (PersistentClient)    │
        │                     │    │                        │
        │  users              │    │  regulatory_kb         │
        │  documents          │    │    global, all users   │
        │  comparisons        │    │                        │
        │  annotations        │    │  user_kb_{safe_uid}    │
        │  kb_documents       │    │    personal, per-user  │
        └─────────────────────┘    └────────────────────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │  OpenAI-compatible  │
                                   │  Embeddings API     │
                                   │  (text-embedding-*) │
                                   └─────────────────────┘
                    ┌───────────────────────────────────┐
                    │   OpenAI-compatible Chat API      │
                    │   GPT-4o  (or any compatible LLM) │
                    │   Semantic analysis + chat + summ │
                    └───────────────────────────────────┘
```

---

## Features

**Document ingestion**
- PDF upload via drag-and-drop with per-file progress tracking
- Text extraction with `pdfplumber`, page count, word count, and section detection
- Documents stored in SQLite/Postgres; no raw files retained server-side

**Multi-stage comparison pipeline**
- **Text diff** — `difflib` paragraph-level diff with inline word-level highlighting for modified blocks; similarity ratio computed via `SequenceMatcher`
- **RAG grounding** — ChromaDB queried against both global (regulatory) and personal knowledge bases before the LLM is called; retrieved chunks are prepended to the analysis prompt so GPT-4o grounds compliance interpretations in authoritative reference material
- **Semantic analysis** — GPT-4o classifies each diff chunk by `change_type` (addition / deletion / modification / regulatory_update), assigns `impact_level` (high / medium / low), and generates `business_impact`, `compliance_impact`, `regulatory_impact`, and `recommendations`
- **Executive summary** — separate GPT-4o call produces `key_changes`, `risk_areas`, and `compliance_flags` from the aggregated analysis
- **Section alignment** — headings extracted from both documents, embedded with the embeddings API, cosine similarity matrix computed, Hungarian-algorithm-style greedy matching used to identify unchanged / modified / added / deleted sections and semantic clone pairs

**Comparison dashboard**
- Semantic changes list with impact badges and expandable per-change detail
- Side-by-side diff viewer with syntax-coloured additions/deletions
- Section analysis panel with similarity matrix heatmap
- Executive summary with risk areas and compliance flags
- RAG context panel showing which knowledge-base chunks influenced the analysis

**Streaming chat**
- Comparison-grounded system prompt built from the full `ComparisonResult`
- Responses streamed token-by-token over SSE; client manages conversation history
- Conversations are volatile by design — no chat history persisted

**Annotations**
- Inline annotations on any semantic change, resolved/unresolved toggle, author tracked via authenticated user

**Export**
- Full PDF report via ReportLab with executive summary, change tables, and annotations
- DOCX report via python-docx with equivalent content

**Knowledge base**
- Upload PDF, TXT, or Markdown files to a global (shared) or personal collection
- Text chunked at ~800 chars with 120-char overlap; stored in ChromaDB with embeddings
- Per-user personal KB keeps proprietary context (internal policies, company-specific regulations) isolated from other users

**Auth**
- JWT bearer tokens, Argon2 password hashing via `pwdlib`
- OAuth2PasswordBearer flow; `GET /api/auth/me` returns current user

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| UI components | lucide-react, framer-motion, react-diff-viewer-continued, react-dropzone, react-markdown |
| Backend | FastAPI, Python 3.12, Uvicorn |
| AI — chat/analysis | OpenAI-compatible API (GPT-4o by default) via `openai` SDK |
| AI — embeddings | OpenAI-compatible embeddings API |
| Token counting | `tiktoken` (cl100k_base) |
| Vector DB | ChromaDB (PersistentClient) |
| Relational DB | SQLite (default, via `aiosqlite`) or Postgres (via `asyncpg`) |
| ORM | SQLAlchemy async |
| PDF extraction | `pdfplumber` |
| Export — PDF | `reportlab` |
| Export — DOCX | `python-docx` |
| Auth | `python-jose` (JWT), `pwdlib[argon2]` |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
policylens/
├── backend/
│   ├── main.py                  # FastAPI app, lifespan, CORS, router registration
│   ├── config.py                # Pydantic Settings (all config from .env)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── database/
│   │   ├── connection.py        # Async engine, session factory, health check
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   └── crud.py              # Async CRUD helpers
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py              # /api/auth — register, login, me
│   │   ├── documents.py         # /api/documents — upload, retrieve
│   │   ├── comparison.py        # /api/comparison — analyze, history, get, delete
│   │   ├── chat.py              # /api/chat — SSE streaming chat
│   │   ├── annotations.py       # /api/annotations — CRUD + resolve
│   │   ├── export.py            # /api/export — PDF and DOCX download
│   │   └── knowledge_base.py    # /api/kb — upload, list, delete, search, stats
│   └── services/
│       ├── text_diff.py         # difflib paragraph + word diff
│       ├── semantic_analyzer.py # GPT-4o semantic analysis + executive summary
│       ├── section_aligner.py   # Embedding-based section matching
│       ├── embeddings.py        # Batched async embedding client
│       ├── rag_service.py       # ChromaDB RAG — chunk, embed, query
│       ├── chat_service.py      # System prompt builder + SSE stream
│       ├── auth_service.py      # JWT + password hashing
│       ├── pdf_extractor.py     # pdfplumber extraction helpers
│       ├── export_pdf.py        # ReportLab PDF generation
│       └── export_docx.py       # python-docx DOCX generation
│
└── frontend/
    ├── app/
    │   ├── page.tsx             # Main upload + results page
    │   ├── history/page.tsx     # Past comparisons
    │   ├── knowledge-base/page.tsx
    │   └── login/page.tsx
    ├── components/
    │   ├── ComparisonDashboard.tsx
    │   ├── SemanticChanges.tsx
    │   ├── DiffViewer.tsx
    │   ├── SectionAnalysis.tsx
    │   ├── SimilarityMatrix.tsx
    │   ├── ExecutiveSummary.tsx
    │   ├── ComparisonChat.tsx   # SSE chat with message history
    │   ├── AnnotationsPanel.tsx
    │   ├── RagContextPanel.tsx
    │   ├── FileDropZone.tsx
    │   ├── AnalyzingOverlay.tsx
    │   ├── ChangeBadge.tsx
    │   └── ImpactBadge.tsx
    ├── context/
    │   └── AuthContext.tsx      # JWT storage, auto-logout, user state
    ├── lib/
    │   ├── api.ts               # Axios wrapper — all API calls
    │   └── utils.ts
    └── types/
        └── index.ts             # Full TypeScript type definitions
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose, **or** Node.js 20+ and Python 3.12+
- An OpenAI API key (or any OpenAI-compatible endpoint, e.g. Azure OpenAI, Groq, local Ollama)
- A ChromaDB instance — either the embedded `PersistentClient` (default, zero config) or a hosted ChromaDB Cloud tenant

### Docker Compose (recommended)

```bash
git clone https://github.com/souviks22/policylens
cd policylens

# 1. Configure the backend
cp backend/.env.example backend/.env
# Edit backend/.env — see Configuration section below

# 2. Configure the frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local

# 3. Start
docker compose up --build
```

Frontend: http://localhost:3000  
Backend API docs: http://localhost:8000/docs

### Manual Setup

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## Configuration

All backend configuration is read from `backend/.env`:

| Variable | Description | Example |
|---|---|---|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `OPENAI_BASE_URL` | Base URL for the chat API | `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | API key for chat completions | `sk-...` |
| `OPENAI_MODEL` | Model name | `gpt-4o` |
| `OPENAI_EMBEDDING_BASE_URL` | Base URL for the embeddings API | `https://api.openai.com/v1` |
| `OPENAI_EMBEDDING_API_KEY` | API key for embeddings | `sk-...` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `MAX_TOKENS` | Max tokens per LLM response | `4096` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `DATABASE_URL` | SQLAlchemy async URL | `sqlite+aiosqlite:///./policylens.db` |
| `JWT_SECRET` | Secret for signing JWTs | (generate with `openssl rand -hex 32`) |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes | `1440` |
| `CHROMA_PATH` | Local path for ChromaDB persistence | `./chroma_db` |
| `CHROMA_API_KEY` | API key if using ChromaDB Cloud | |
| `CHROMA_TENANT_ID` | Tenant ID for ChromaDB Cloud | |
| `CHROMA_DATABASE_NAME` | Database name for ChromaDB Cloud | |
| `RAG_TOP_K` | Max chunks retrieved per query | `8` |
| `RAG_SCORE_THRESHOLD` | Minimum relevance score to include a chunk | `0.4` |
| `RAG_MAX_CONTEXT_CHARS` | Max characters of RAG context injected into prompts | `6000` |

**Using a different LLM** — because the backend uses the `openai` SDK with a configurable `base_url`, you can point it at any OpenAI-compatible endpoint. Set `OPENAI_BASE_URL` and `OPENAI_MODEL` accordingly. The semantic analysis and chat features are the only parts that call the chat API; embedding calls go to the separate `OPENAI_EMBEDDING_*` variables, so you can mix providers.

**Using Postgres instead of SQLite** — set `DATABASE_URL` to a `postgresql+asyncpg://...` connection string and ensure `asyncpg` is installed.

---

## API Reference

Full interactive docs are available at `http://localhost:8000/docs` (Swagger UI) and `/redoc`.

### Authentication

```
POST /api/auth/register   { username, password, full_name? }  →  TokenResponse
POST /api/auth/login      form: username + password           →  TokenResponse
GET  /api/auth/me                                             →  UserResponse
```

All other endpoints require `Authorization: Bearer <token>`.

### Documents

```
POST /api/documents/upload    multipart/form-data: file  →  UploadResponse
GET  /api/documents/{id}                                  →  document text + metadata
```

### Comparison

```
POST /api/comparison/analyze   { doc1_id, doc2_id }  →  ComparisonResult
GET  /api/comparison/history                         →  ComparisonListItem[]
GET  /api/comparison/{id}                            →  ComparisonResult
DELETE /api/comparison/{id}
```

`ComparisonResult` includes: `diff_chunks`, `semantic_changes`, `summary`, `section_analysis`, `text_similarity_ratio`, and `rag_context` (which chunks from the knowledge base influenced the analysis).

### Chat

```
POST /api/chat/{comparison_id}   { messages: [{role, content}] }
```

Returns `text/event-stream`. The client sends the full conversation history on every request. Responses are streamed as SSE `data:` events.

### Knowledge Base

```
POST   /api/kb/upload                multipart: file, scope (global|personal), description?
GET    /api/kb/documents             →  KbDocument[]
DELETE /api/kb/documents/{doc_id}
GET    /api/kb/search?q=<query>      →  KbSearchResult[]  (preview retrieval)
GET    /api/kb/stats                 →  { global_chunks, personal_chunks }
```

### Annotations

```
POST   /api/annotations/                        { comparison_id, change_id, text, author? }
PATCH  /api/annotations/{id}/resolve
DELETE /api/annotations/{id}
```

### Export

```
GET /api/export/{comparison_id}/pdf    →  application/pdf
GET /api/export/{comparison_id}/docx  →  application/vnd.openxmlformats-officedocument...
```

### Health

```
GET /health  →  { status, database: { status }, vector_db: { status } }
```

---

## How the Analysis Pipeline Works

When you click **Analyze**, the backend runs five sequential steps:

1. **Text diff** (`TextDiffService`) — the two document texts are split into paragraphs and compared with `difflib.SequenceMatcher`. Each differing block becomes a `DiffChunk` tagged as `addition`, `deletion`, or `modification`. For large modified blocks a second word-level pass identifies the exact inline changes.

2. **RAG retrieval** (`RAGService`) — a query string is synthesised from the two documents' filenames and opening text. ChromaDB is queried against the global `regulatory_kb` collection (shared across all users) and the current user's `user_kb_{uid}` collection. Results below `RAG_SCORE_THRESHOLD` are discarded. The surviving chunks are formatted into a context block and injected into the LLM prompts in steps 3 and 4. This step is best-effort; a ChromaDB failure does not abort the comparison.

3. **Semantic analysis** (`SemanticAnalyzer`) — the top-25 most significant diff chunks plus the RAG context are sent to GPT-4o. The model returns structured JSON with a `SemanticChange` per chunk: `change_type`, `impact_level` (high / medium / low), `business_impact`, `compliance_impact`, `regulatory_impact`, and `recommendations`. Token budget is managed with `tiktoken`.

4. **Executive summary** — a second GPT-4o call receives the aggregated semantic changes and RAG context and produces a `ComparisonSummary`: overall impact level, `key_changes` list, `risk_areas`, and `compliance_flags`.

5. **Section alignment** (`SectionAligner`) — headings are extracted from both documents via regex. Each heading + its content body is embedded with the embeddings API (batched, up to 64 texts per call). A full cosine similarity matrix is computed. Greedy matching assigns each section to its best counterpart above a similarity threshold, yielding a `SectionMatch[]` with `unchanged` / `modified` / `added` / `deleted` types plus `semantic_clone_pairs` for sections that are near-identical despite appearing in different positions.

The full `ComparisonResult` is persisted to the relational database and cached in-process. Subsequent reads hit the in-memory cache.

---

## Knowledge Base

The knowledge base lets you prime the RAG layer with authoritative reference material so the semantic analysis is grounded in your specific regulatory environment.

**Global KB** — documents uploaded to the global scope are available to all users. Use this for public regulatory texts, industry standards, or compliance frameworks (e.g. GDPR, HIPAA, ISO 27001).

**Personal KB** — documents uploaded to the personal scope are only retrieved when the uploader runs a comparison. Use this for internal policies, company-specific procedures, or proprietary compliance frameworks.

Documents are chunked at ~800 characters with 120-character overlap and embedded on upload. The ChromaDB collection for each scope is queried at comparison time; chunks that score above `RAG_SCORE_THRESHOLD` are included in the analysis prompt. The `RagContextPanel` in the dashboard shows which specific chunks were used and their relevance scores.

---

## Development Notes

**In-memory result cache** — `comparison.py` maintains `_result_cache` and `_analysis_cache` as module-level dicts. This avoids deserialising large JSON blobs on every request within a single process. The cache is not shared across workers; for multi-worker deployments, rely on the database read path.

**Async + sync boundary** — ChromaDB's `PersistentClient` is synchronous. All ChromaDB calls in `RAGService` are dispatched to the asyncio thread-pool executor via `loop.run_in_executor`. Similarly, `pdfplumber` extraction runs in an executor to avoid blocking the event loop.

**OpenAI SDK compatibility** — the backend sets `base_url` on the `AsyncOpenAI` client, making it trivial to swap in any OpenAI-compatible provider. Chat and embeddings use separate client instances so they can point to different providers or models.

**Token budgeting** — `SemanticAnalyzer` uses `tiktoken` with the `cl100k_base` encoding to count tokens and truncate document excerpts before they are sent to the model, preventing context-window overflows on large PDFs.

**Streaming chat** — `ChatService.stream()` yields raw SSE `data:` lines. The FastAPI endpoint wraps this in a `StreamingResponse` with `media_type="text/event-stream"` and `X-Accel-Buffering: no` to prevent proxy buffering. The frontend `ComparisonChat` component reads the stream with `ReadableStream` and appends tokens incrementally.
