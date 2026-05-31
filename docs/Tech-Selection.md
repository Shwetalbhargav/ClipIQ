# Tech Selection: ClipIQ

## 1. Selected Stack

| Layer | Selection | Reason |
| --- | --- | --- |
| Frontend | React with JavaScript | Required, fast iteration, broad ecosystem |
| Backend | FastAPI | Python-native AI stack, async streaming support |
| Workflow orchestration | LangGraph | Explicit stateful graph for RAG, memory, retrieval, and generation |
| LLM | GPT-4o-mini | Cost-effective streaming model for RAG chat |
| Vector database | Qdrant | Strong filtering, production-ready vector search, self-host or managed |
| Document database | MongoDB | Durable source of truth with flexible video, transcript, metadata, and chat documents |
| Embeddings | OpenAI text embedding model | Reliable managed embeddings with simple integration |
| Streaming | Server-Sent Events | Best fit for one-way streamed chat in MVP |
| Background work | Celery/RQ/Dramatiq or cloud queue | Needed for extraction and transcription at scale |

## 2. Frontend: React JavaScript

Why:

- Meets the requirement directly.
- Vite-based React is lightweight and quick for MVP.
- Component model fits video cards, chat streams, citations, and status panels.

Tradeoffs:

- JavaScript lacks compile-time API contract checks.
- TypeScript would reduce integration bugs as the API evolves.

Mitigation:

- Use API response validators.
- Keep API types documented in OpenAPI.
- Add focused frontend tests for streaming and error states.

## 3. Backend: FastAPI

Why:

- Python ecosystem aligns with LangGraph, Qdrant clients, OpenAI SDK, transcript processing, and media tooling.
- OpenAPI documentation comes built in.
- Async streaming is straightforward.

Tradeoffs:

- Long extraction jobs should not run inside request handlers.
- CPU-heavy transcription can block workers if not isolated.

Mitigation:

- Run extraction/indexing in background workers.
- Keep API workers focused on request handling and streaming.
- Use job status records in MongoDB.

## 4. LangGraph

Why:

- RAG chat has state: comparison, memory, query, retrieved chunks, metadata, citations, final answer.
- LangGraph makes the state transitions explicit and testable.
- It supports future branching such as metadata-only fallback or answer verification.

Tradeoffs:

- More structure than a simple LangChain chain.
- Requires discipline around graph state schema and node boundaries.

Mitigation:

- Keep MVP graph small.
- Define typed state objects.
- Test nodes independently.

## 5. GPT-4o-mini

Why:

- Good quality-to-cost ratio for RAG chat.
- Supports streaming.
- Strong enough for transcript comparison, summarization, and recommendations.

Tradeoffs:

- May miss nuanced strategy analysis compared with larger models.
- Still needs retrieval grounding and citation control.

Mitigation:

- Use strict prompts with evidence sections.
- Include citation IDs in context.
- Add optional premium path later using a stronger model for final reports.

## 6. Qdrant

Why:

- Designed for vector search with rich payload filtering.
- Comparison/session filtering is critical for preventing source leakage.
- Can run locally with Docker or as a managed service.
- Good operational features for production scaling.

Tradeoffs:

- Adds another datastore to operate.
- MongoDB plus Atlas Vector Search could be simpler for teams already standardized on MongoDB.

Why not pgvector for MVP:

- Atlas Vector Search is attractive when simplifying infrastructure matters most.
- Qdrant is a better fit when vector filtering, collection management, and vector operations are first-class needs.

Mitigation:

- Keep MongoDB as source of truth.
- Store Qdrant point IDs in MongoDB.
- Make indexing idempotent.

## 7. MongoDB

Why:

- The app has document-shaped data: sessions, videos, metrics snapshots, transcript segments, chat turns, citations, and raw extractor payloads.
- Flexible documents fit platform metadata that changes by source and extractor.
- Supports operational querying and future creator analytics when indexes are designed intentionally.

Tradeoffs:

- Requires careful schema discipline even though the database is schemaless by default.
- Cross-document joins and complex analytics are less natural than in a relational database.

Mitigation:

- Use explicit document schemas in the application layer.
- Embed data that is read together, such as video metadata and current metrics, and reference large or independently updated collections.
- Add indexes for comparison, video, creator, and created-at query paths from day one.

## 8. Transcript and Metadata Extraction

Recommended approach:

- Use official APIs where practical for metadata.
- Use caption/transcript extraction for YouTube.
- Support Instagram Reel extraction behind an adapter interface.
- Add speech-to-text fallback for missing transcripts.

Tradeoffs:

- Official APIs are stable but limited and require credentials.
- Unofficial extractors are faster for demos but brittle.
- Speech-to-text improves coverage but adds cost and latency.

Decision:

- Build an extraction interface first.
- Treat each platform extractor as replaceable.
- Record extraction source and confidence.

## 9. Streaming: SSE vs WebSockets

Selected: Server-Sent Events.

Why:

- The main streaming path is server-to-browser token output.
- Easier to implement and debug.
- Works well with HTTP infrastructure.

Tradeoffs:

- Less flexible for bidirectional realtime interactions.
- Cancellation and job progress can be less elegant.

When to switch:

- Collaborative sessions.
- Real-time extraction progress with many event types.
- Complex cancellation and control messages from the client.

## 10. Memory

Selected:

- Store chat messages in MongoDB.
- Load recent turns into LangGraph state.
- Summarize older turns when conversations grow.

Tradeoffs:

- Full-history memory increases token cost.
- Summary memory can lose details.

Mitigation:

- Keep the last N turns verbatim.
- Maintain a rolling summary.
- Always retrieve source chunks again for factual claims.
