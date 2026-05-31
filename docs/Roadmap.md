# Roadmap

## Phase 0: Foundation

Goal:

Define the target architecture and prepare the codebase for a production-shaped MVP.

Deliverables:

- Requirements, architecture, tech-selection, costing, and decision docs.
- Environment configuration for OpenAI, MongoDB, and Qdrant.
- Local Docker Compose for MongoDB and Qdrant.
- Database migration setup.
- Backend configuration module.

Exit criteria:

- Developers can run backend, frontend, MongoDB, and Qdrant locally.
- Secrets are documented through `.env.example`.

## Phase 1: Core Data Model and API

Goal:

Create the durable backend foundation.

Deliverables:

- MongoDB collections for comparisons, videos, metrics, transcripts, chunks, chat messages, and citations.
- MongoDB ODM or repository persistence layer.
- FastAPI endpoints:
  - `POST /api/comparisons`
  - `GET /api/comparisons/{comparison_id}`
  - `POST /api/comparisons/{comparison_id}/chat/stream`
  - `GET /api/health`
- URL validation and normalization.
- Engagement-rate calculation service.

Exit criteria:

- A comparison can be created and fetched.
- Metrics can be persisted and engagement rate can be tested.

## Phase 2: Extraction Pipeline

Goal:

Extract metadata and transcripts from one YouTube URL and one Instagram Reel URL.

Deliverables:

- Platform extractor interface.
- YouTube extractor.
- Instagram Reel extractor.
- Transcript normalization.
- Metadata normalization.
- Partial failure handling.
- Raw extraction payload storage.

Exit criteria:

- The system can process a real YouTube URL and a real Instagram Reel URL.
- Missing fields are represented as unavailable, not zero.
- Extraction status is visible through the API.

## Phase 3: Qdrant Indexing

Goal:

Store searchable transcript chunks in Qdrant.

Deliverables:

- Chunking service.
- Embedding service.
- Qdrant collection setup.
- Payload indexes for comparison and video filters.
- Idempotent indexing.
- MongoDB linkage to Qdrant point IDs.

Exit criteria:

- Transcript chunks are embedded and searchable.
- Retrieval is filtered to a single comparison.
- Re-running indexing does not duplicate chunks.

## Phase 4: LangGraph Chat

Goal:

Answer comparison questions using memory, metadata, retrieved transcript chunks, and GPT-4o-mini.

Deliverables:

- LangGraph state schema.
- Nodes for memory loading, retrieval, context building, streaming generation, and persistence.
- Prompt template with citation rules.
- Source citation format.
- Chat memory persistence.
- SSE streaming endpoint.

Exit criteria:

- User asks a question and receives a streamed answer.
- Answer cites video/chunk sources.
- Follow-up questions use prior chat context.

## Phase 5: React Frontend

Goal:

Build a usable comparison and chat experience.

Deliverables:

- URL input form.
- Extraction progress states.
- Side-by-side video cards.
- Engagement-rate display.
- Chat panel with streaming response rendering.
- Citation display with timestamps when available.
- Error states for blocked extraction or missing transcript.

Exit criteria:

- A user can complete the full workflow from the browser.
- Partial extraction states are understandable.
- Streamed responses render without waiting for completion.

## Phase 6: Production Readiness

Goal:

Prepare the app for moderate real usage.

Deliverables:

- Background job queue.
- Worker process for extraction/transcription/indexing.
- Retry policy.
- Provider timeout handling.
- Observability for extraction, indexing, retrieval, token usage, and errors.
- Rate limits and user quotas.
- Cache by normalized video ID.

Exit criteria:

- API remains responsive during extraction.
- Failed jobs can retry safely.
- Operators can identify platform/provider failures.

## Phase 7: Scaling to 1,000 Creators per Day

Goal:

Scale usage without linear cost or reliability degradation.

Deliverables:

- Managed MongoDB configuration.
- Managed or clustered Qdrant.
- Autoscaled workers.
- Metrics refresh policy.
- Transcript cache policy.
- Cost dashboard.
- Per-user and global provider budgets.

Exit criteria:

- 1,000 daily comparisons can be processed within provider and infrastructure limits.
- Cached videos avoid duplicate extraction and embedding.
- Cost per comparison is measurable and bounded.

## Phase 8: Product Enhancements

Potential enhancements:

- Side-by-side transcript timeline.
- Highlight matched moments across both videos.
- Report export.
- Larger-model analysis mode.
- Creator account integrations.
- Team workspaces.
- Saved prompt templates.
- Batch comparisons.
- A/B creative recommendations.

Decision rule:

Only add enhancements after the core loop is reliable: submit URLs, extract evidence, compute metrics, retrieve accurately, stream cited answers, and preserve memory.
