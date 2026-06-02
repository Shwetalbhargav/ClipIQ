# ClipIQ Backend

ClipIQ compares one YouTube video with one Instagram Reel, builds a transcript-backed RAG index, and lets creators ask grounded questions about engagement, hooks, metadata, and improvement ideas.

## Stack

- FastAPI
- LangGraph orchestration
- OpenAI chat + embeddings
- Qdrant vector database
- MongoDB for comparisons, videos, metrics, transcripts, chunks, and chat memory
- `yt-dlp`, `youtube-transcript-api`, and optional Whisper fallback for extraction

## Environment

Copy `.env.example` to `.env` and fill values:

```powershell
APP_NAME=ClipIQ
APP_ENV=development
API_PREFIX=/api
BACKEND_CORS_ORIGINS=http://localhost:5173

OPENAI_API_KEY=...
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=clipiq

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH=(Get-Location).Path
python -m uvicorn app.main:app --reload --port 8000
```

## Docker Setup

From this backend folder:

```powershell
docker compose up --build
```

The API runs on `http://localhost:8000`; Qdrant runs on `http://localhost:6333`.

## API Routes

- `GET /api/health`
- `POST /api/comparisons`
- `GET /api/comparisons/{comparison_id}`
- `POST /api/chat`
- `POST /api/comparisons/{comparison_id}/chat/stream`
- `POST /api/videos/analyze` for metadata-only legacy analysis

## Create A Comparison

`POST /api/comparisons`

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "instagram_url": "https://www.instagram.com/reel/CxYz123abcd/"
}
```

The response includes `comparison_id`, status, Video A/B summaries, engagement metrics, transcript/indexing status, and errors when the comparison is partial.

Video A is always YouTube. Video B is always Instagram.

## Stream Chat

`POST /api/comparisons/{comparison_id}/chat/stream`

```json
{
  "message": "Compare the hooks in the first 5 seconds."
}
```

The endpoint emits Server-Sent Events:

- `metadata`
- `delta`
- `citation`
- `done`
- `error`

## Tests

```powershell
$env:PYTHONPATH=(Get-Location).Path
python -m pytest -q
```

## Scaling And Cost Notes

For 1000 creators/day, the lowest-cost high-quality path is caption-first extraction, short transcript chunks, batched embeddings, and filtered Qdrant retrieval. Most videos are short, so embedding cost stays small with `text-embedding-3-small`; GPT-4o-mini is the default chat model because the answer quality is good enough when metadata and transcript context are structured.

The expensive path is Whisper fallback. Keep it behind duration limits, prefer captions/subtitles first, and cache canonical video URLs so repeated demos or creator retries do not re-embed the same transcript. Qdrant payload filters isolate each comparison and keep retrieval fast. MongoDB remains the source of truth; Qdrant only stores searchable chunks.

At higher volume, move `POST /api/comparisons` to enqueue extraction/indexing jobs, return `processing`, and let the frontend poll `GET /api/comparisons/{comparison_id}`. For the screening demo, the synchronous flow is easier to demonstrate and still uses production-shaped persistence and indexing.

## Platform Risks

YouTube captions are usually available through `youtube-transcript-api` or `yt-dlp` subtitles, but some videos disable transcripts. Instagram public metadata and captions are less stable; `yt-dlp` may need cookies or may fail when Instagram changes access rules. Missing metrics stay `null`, never fabricated as zero, and partial comparisons are returned instead of crashing.
