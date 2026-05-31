# ClipIQ

Full-stack RAG chatbot for comparing a YouTube video against an Instagram Reel. The app extracts metadata and transcripts, computes engagement rate, indexes transcript chunks in ChromaDB, and streams source-cited answers through a LangGraph workflow.

## Stack
- Frontend: React + Vite
- Backend: FastAPI
- Orchestration: LangGraph
- LLM: Groq-hosted Llama
- Embeddings: OpenAI embeddings
- Vector DB: ChromaDB
- Extraction: `yt-dlp` captions/metadata with Whisper fallback

## Setup

```bash
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Run backend tests from the `backend` folder:

```bash
py -m pytest
```

## Environment

Required for a real demo:
- `GROQ_API_KEY`
- `OPENAI_API_KEY`

Optional:
- `INSTAGRAM_COOKIES_FILE`: Netscape-format cookies file for restricted Reels.
- `CHROMA_PATH`: local persistent ChromaDB directory.
- `ALLOW_FAKE_EMBEDDINGS=true`: development-only deterministic embeddings for tests without OpenAI.

## API

`POST /api/videos/analyze`

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "instagram_url": "https://www.instagram.com/reel/..."
}
```

`POST /api/chat/stream`

```json
{
  "session_id": "uuid",
  "message": "Why did Video A get more engagement than Video B?"
}
```

`GET /api/session/{session_id}`

Returns video cards and chat history for a session.

## Engineering Tradeoffs

Groq-hosted Llama gives very fast streaming without requiring a local GPU, while still satisfying the Llama runtime requirement. OpenAI embeddings are reliable and inexpensive for transcript-sized workloads. ChromaDB is the fastest local demo path because it avoids managed infrastructure, credentials, and network latency; for production, Qdrant or Pinecone would be the better fit for multi-instance deployments and operational monitoring.

The extractor prefers platform captions when available because they are cheap and fast. Whisper fallback covers videos without captions, at the cost of transcription latency and audio download complexity. Instagram public metadata can be restricted, so the backend supports a cookie file and returns explicit extraction errors when the platform blocks access.

## Scaling to 1000 Creators per Day

For production, video extraction and transcription should move to background workers behind a queue. Results should be cached by normalized video URL so repeated creator comparisons do not re-download or re-transcribe the same media. ChromaDB should be replaced by a managed vector database or a Qdrant cluster, and metadata should live in MongoDB. Rate limits need provider-specific retry policies, per-user quotas, and fallbacks for LLM and transcription providers.

## Demo Checklist

- Submit one YouTube URL and one Instagram Reel URL.
- Confirm both cards show metadata and engagement rate.
- Ask the required comparison questions.
- Confirm answers stream and include Video A/B chunk citations.
- Explain the scaling and cost tradeoffs from this README in the Loom.
