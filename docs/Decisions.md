# Architecture Decisions

## ADR-001: Use FastAPI for the Backend

Status: Accepted

Decision:

Use FastAPI as the backend API framework.

Reasoning:

- Python is the strongest fit for LangGraph, OpenAI SDKs, Qdrant clients, and transcript/media tooling.
- FastAPI gives OpenAPI docs, request validation, async endpoints, and streaming support.
- It is lightweight enough for MVP but production capable behind a real ASGI server.

Tradeoffs:

- Long-running extraction must be moved out of request handlers.
- Python async code requires care when calling blocking media tools.

Consequences:

- Use background workers for extraction, transcription, and indexing.
- Keep API handlers thin.

## ADR-002: Use React with JavaScript for the Frontend

Status: Accepted

Decision:

Build the frontend in React using JavaScript.

Reasoning:

- Matches the stated requirement.
- React is well suited to streaming chat UIs and side-by-side comparison views.

Tradeoffs:

- JavaScript does not provide TypeScript's compile-time API safety.

Consequences:

- Use OpenAPI documentation and runtime validation patterns.
- Consider TypeScript migration when the frontend grows.

## ADR-003: Use MongoDB as the Source of Truth

Status: Accepted

Decision:

Use MongoDB for durable application data.

Reasoning:

- The application stores document-shaped data for comparisons, videos, metrics snapshots, transcripts, chat turns, citations, and raw extractor payloads.
- MongoDB fits flexible platform metadata where available fields vary by source and extractor.

Tradeoffs:

- Requires application-level schema discipline and intentional indexing.

Consequences:

- Store raw extraction payloads as nested documents, but keep core query fields promoted and indexed.
- Store Qdrant point IDs in MongoDB to support reindexing and traceability.

## ADR-004: Use Qdrant for Vector Search

Status: Accepted

Decision:

Use Qdrant for transcript chunk embeddings and vector retrieval.

Reasoning:

- Qdrant provides strong vector search and payload filtering.
- Session-scoped filtering is central to source isolation.
- It can run locally or as a managed service.

Tradeoffs:

- Adds another datastore to operate.
- pgvector would simplify infrastructure for small workloads.

Consequences:

- MongoDB remains the source of truth.
- Qdrant stores retrievable chunks and metadata payloads.
- Indexing must be idempotent.

## ADR-005: Use LangGraph for RAG Orchestration

Status: Accepted

Decision:

Use LangGraph to orchestrate chat, retrieval, memory, and generation.

Reasoning:

- The workflow has explicit state and branching needs.
- LangGraph makes retrieval, memory loading, fallback handling, and persistence testable as separate nodes.

Tradeoffs:

- More complexity than a single function or simple chain.

Consequences:

- Define a small graph for MVP.
- Add nodes only when they represent a real branch or state transition.

## ADR-006: Use GPT-4o-mini for Response Generation

Status: Accepted

Decision:

Use GPT-4o-mini as the default chat generation model.

Reasoning:

- Good cost-performance fit for streamed RAG answers.
- Strong enough for comparison, summarization, and source-grounded recommendations.

Tradeoffs:

- A larger model may provide deeper strategic analysis.

Consequences:

- Keep prompts evidence-first.
- Add a larger-model premium path later if needed.

## ADR-007: Use Server-Sent Events for Streaming

Status: Accepted

Decision:

Use SSE for streamed chat responses.

Reasoning:

- Chat output is primarily one-way from server to client.
- SSE is simpler than WebSockets for MVP.

Tradeoffs:

- Less flexible for bidirectional real-time control.

Consequences:

- Use SSE for token deltas and citations.
- Reconsider WebSockets if live collaborative features or richer job control appear.

## ADR-008: Citation-First RAG Answers

Status: Accepted

Decision:

Answers must cite transcript chunks or metadata sources.

Reasoning:

- The product's trust depends on showing why an answer was produced.
- Video comparison claims can be subjective; citations reduce unsupported speculation.

Tradeoffs:

- Citation enforcement adds prompt and persistence complexity.
- Some useful strategy advice may not map cleanly to a single source.

Consequences:

- Every retrieved chunk gets a stable citation ID.
- Metadata-only claims must cite metadata records.
- Unsupported claims should be framed as hypotheses.

## ADR-009: Caption-First Transcript Extraction

Status: Accepted

Decision:

Prefer platform captions/transcripts before speech-to-text fallback.

Reasoning:

- Captions are faster and cheaper.
- Speech-to-text can dominate cost and latency.

Tradeoffs:

- Caption quality may vary.
- Some videos will have no usable transcript.

Consequences:

- Store transcript source type.
- Make fallback transcription configurable.
- Continue with metadata-only comparison when transcript is unavailable.
