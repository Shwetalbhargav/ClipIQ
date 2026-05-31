# Architecture: ClipIQ

## 1. System Overview

ClipIQ is a session-based RAG system. A user submits one YouTube URL and one Instagram Reel URL. The backend extracts metadata and transcripts, computes engagement metrics, stores durable records in MongoDB, writes transcript embeddings into Qdrant, and runs a LangGraph workflow for source-grounded streamed chat answers.

```text
React frontend
  -> FastAPI API
    -> extraction services
    -> MongoDB
    -> embedding service
    -> Qdrant
    -> LangGraph chat workflow
      -> retriever
      -> GPT-4o-mini streaming
```

## 2. Major Components

### React Frontend

Responsibilities:

- Capture YouTube and Instagram Reel URLs.
- Start comparison analysis.
- Render extraction status and video metadata.
- Display engagement-rate comparison.
- Send chat questions.
- Render streamed assistant output.
- Show citations with video labels and timestamps.

Reasoning:

- React with JavaScript is fast to build and easy to staff.
- For this product, TypeScript would reduce frontend defects, but the stated requirement is JavaScript. Use JSDoc and runtime API validation if the codebase grows.

### FastAPI Backend

Responsibilities:

- Expose REST and streaming endpoints.
- Validate URLs.
- Coordinate extraction and indexing.
- Persist comparison, video, transcript, chat, and citation records.
- Run LangGraph for chat.
- Stream GPT-4o-mini responses.

Reasoning:

- FastAPI fits Python-first AI workflows.
- Python has strong support for LangGraph, Qdrant, OpenAI SDKs, media tooling, and transcript processing.
- Async endpoints are useful for streaming, but CPU-heavy or long-running extraction should move to workers.

### Extraction Layer

Responsibilities:

- Normalize input URLs.
- Extract platform metadata.
- Extract transcripts/captions.
- Convert platform-specific fields into a common internal schema.
- Record unavailable fields without inventing data.

Potential implementations:

- YouTube: official YouTube Data API for metadata when possible, caption/transcript library or yt-dlp fallback.
- Instagram Reels: official APIs are limited for arbitrary public Reels; browser/yt-dlp-style extraction may work for demos but carries platform risk.
- Speech-to-text fallback: Whisper or another transcription provider for videos without captions.

Tradeoff:

- Unofficial extraction is faster for MVP but less reliable and may violate platform constraints depending on usage. Official APIs are safer but often provide less transcript access and require account authorization.

### MongoDB

Responsibilities:

- Store durable system-of-record data:
  - comparisons
  - videos
  - metadata snapshots
  - transcript segments
  - engagement metrics
  - chat messages
  - citations
  - extraction jobs

Reasoning:

- MongoDB handles flexible video, metadata, transcript, chat, and extraction documents better than keeping everything in the vector database.
- Qdrant should store vector-search payloads, not become the main application database.

### Qdrant

Responsibilities:

- Store transcript chunk embeddings.
- Store retrieval payload metadata.
- Support filtered similarity search by comparison/session/video.

Recommended collection:

```text
video_transcript_chunks
```

Payload fields:

- `comparison_id`
- `video_id`
- `platform`
- `source_url`
- `creator`
- `chunk_index`
- `start_seconds`
- `end_seconds`
- `text`
- `metadata_version`

Reasoning:

- Qdrant is a strong production vector store with filtering, payload indexes, snapshots, and managed/self-host options.
- Keeping Qdrant session-filtered avoids cross-session leakage.

### LangGraph

Responsibilities:

- Represent chat as an explicit state machine.
- Load comparison and memory.
- Retrieve transcript chunks.
- Merge structured metadata.
- Generate grounded prompt.
- Stream GPT-4o-mini response.
- Persist assistant response and citations.

Suggested graph:

```text
start
  -> load_comparison
  -> load_memory
  -> retrieve_chunks
  -> build_context
  -> generate_streaming_answer
  -> persist_turn
  -> end
```

Future graph nodes:

- query rewrite
- source sufficiency check
- metadata-only fallback
- citation verifier
- content strategy recommendation formatter

### GPT-4o-mini

Responsibilities:

- Generate concise, source-grounded comparison answers.
- Follow citation format.
- Use retrieved transcript and metadata evidence.
- Ask for clarification when evidence is insufficient.

Reasoning:

- GPT-4o-mini is cost-effective for high-volume chat and good enough for summarization, comparison, and recommendation-style RAG.
- For high-stakes brand strategy reports, a larger model can be added as an optional premium path.

## 3. Data Model

### comparisons

- `id`
- `youtube_url`
- `instagram_url`
- `status`
- `created_at`
- `updated_at`

### videos

- `id`
- `comparison_id`
- `platform`
- `source_url`
- `platform_video_id`
- `creator`
- `title`
- `published_at`
- `duration_seconds`
- `thumbnail_url`
- `raw_metadata`
- `created_at`

### video_metrics

- `id`
- `video_id`
- `views`
- `likes`
- `comments`
- `shares`
- `saves`
- `engagement_rate`
- `engagement_formula`
- `captured_at`

### transcript_segments

- `id`
- `video_id`
- `segment_index`
- `start_seconds`
- `end_seconds`
- `text`
- `source_type`

### transcript_chunks

- `id`
- `video_id`
- `chunk_index`
- `start_seconds`
- `end_seconds`
- `text`
- `qdrant_point_id`
- `embedding_model`

### chat_messages

- `id`
- `comparison_id`
- `role`
- `content`
- `created_at`

### citations

- `id`
- `chat_message_id`
- `video_id`
- `chunk_id`
- `citation_label`
- `start_seconds`
- `end_seconds`
- `quoted_text`

## 4. Key Flows

### Analysis Flow

1. User submits URLs.
2. Backend validates and normalizes URLs.
3. Backend creates comparison record.
4. Extraction jobs run for YouTube and Instagram.
5. Metadata is normalized and persisted.
6. Engagement rate is calculated and persisted.
7. Transcript segments are normalized and persisted.
8. Transcript chunks are created.
9. Chunks are embedded.
10. Embeddings and payloads are written to Qdrant.
11. Comparison status becomes ready, partial, or failed.

### Chat Flow

1. User sends a question for a comparison.
2. Backend appends user message to MongoDB.
3. LangGraph loads comparison state and memory.
4. Retriever searches Qdrant with comparison filter.
5. Backend fetches structured metadata from MongoDB.
6. Prompt is built with citations and rules.
7. GPT-4o-mini response streams to frontend.
8. Final assistant message and citation records are persisted.

## 5. Streaming Design

Use Server-Sent Events for MVP:

- It is simpler than WebSockets.
- Chat generation is server-to-client streaming.
- Browser EventSource or fetch streaming can handle output.

Event types:

- `metadata`: response ID, model, comparison ID.
- `delta`: token text.
- `citation`: citation object.
- `done`: final status and usage.
- `error`: recoverable or terminal failure.

WebSockets become useful later if the app needs bidirectional live job updates, collaborative sessions, or user cancellation that must be immediate.

## 6. Deployment Shape

MVP:

- React static app.
- FastAPI service.
- MongoDB database.
- Qdrant service.
- Optional Redis for background job queue.

Production:

- React on CDN or frontend host.
- FastAPI behind load balancer.
- Worker pool for extraction/transcription/indexing.
- Managed MongoDB.
- Managed or clustered Qdrant.
- Queue such as Redis Queue, Celery, Dramatiq, or cloud-native queue.
- Object storage for temporary media and transcript artifacts.

## 7. Failure Modes

- YouTube transcript unavailable: continue with metadata and optional transcription fallback.
- Instagram blocked: mark video extraction failed and show specific remediation.
- Missing views: engagement rate is unavailable, not zero.
- Qdrant write failure: keep MongoDB records and retry indexing.
- GPT stream interruption: persist partial assistant message with failed status.
- Retrieval returns weak evidence: answer with limitation and cite available metadata.
