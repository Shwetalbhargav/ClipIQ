# Requirements: ClipIQ

## 1. Product Goal

Build ClipIQ, a full-stack application that accepts one YouTube URL and one Instagram Reel URL, extracts transcript and metadata from both videos, calculates engagement metrics, stores searchable transcript embeddings in Qdrant, and lets a user ask streaming, source-cited comparison questions through a LangGraph-powered RAG chatbot.

The primary user is a creator, marketer, analyst, or agency operator who wants to understand why one short-form video performed better than another and what can be learned from the content, metadata, timing, and engagement patterns.

## 2. In Scope

- Accept exactly one YouTube URL and one Instagram Reel URL per comparison session.
- Extract transcript text for each video when available.
- Extract normalized metadata for each video.
- Calculate engagement rate from available public metrics.
- Chunk transcripts and store embeddings in Qdrant.
- Store durable application data in MongoDB.
- Use LangGraph for the comparison and chat workflow.
- Use GPT-4o-mini for streamed answer generation.
- Use FastAPI for the backend API.
- Use React with JavaScript for the frontend.
- Stream chatbot responses to the browser.
- Maintain session memory across the comparison conversation.
- Cite sources in chatbot answers.

## 3. Out of Scope for MVP

- Multi-video batch comparisons.
- Creator account login and private account analytics.
- Paid social API integrations for first-party analytics.
- Automated posting or content generation.
- Long-term social listening across entire creator profiles.
- Fine-tuning models.
- Replacing human judgment with a performance guarantee.

## 4. Functional Requirements

### URL Intake

- The frontend must show two URL inputs:
  - YouTube video URL.
  - Instagram Reel URL.
- The backend must validate platform and URL shape before extraction.
- The system must reject unsupported sources with actionable errors.
- Duplicate URLs should be normalized so repeated comparisons can reuse existing extraction results.

### Metadata Extraction

For each video, the system should extract the best available values for:

- Source platform.
- Source URL.
- Platform video ID or shortcode.
- Title or caption.
- Creator handle or channel name.
- Published date.
- Duration.
- View count or play count.
- Like count.
- Comment count.
- Share count when available.
- Hashtags.
- Thumbnail URL.
- Raw extraction payload for debugging and reprocessing.

Extraction availability varies by platform. The system must distinguish between a metric that is genuinely zero and a metric that is unavailable.

### Transcript Extraction

- Prefer platform-provided captions/transcripts when available.
- Use automatic captions when manual captions are unavailable.
- Fall back to audio download plus speech-to-text only when allowed and configured.
- Store transcript segments with:
  - Text.
  - Start time.
  - End time.
  - Segment index.
  - Source video reference.
- If a transcript cannot be extracted, the system should still allow metadata-based comparison and clearly mark transcript coverage as unavailable.

### Engagement Rate

The MVP engagement rate should be:

```text
engagement_rate = ((likes + comments) / views) * 100
```

Rules:

- Use `views` for YouTube and `plays` or `view_count` for Instagram when available.
- Return `null` when denominator is missing or zero.
- Store the formula version used.
- Display unavailable metrics explicitly instead of fabricating values.

Future formula variants may include shares, saves, subscriber count, follower count, or platform-specific weights.

### Embeddings and Retrieval

- Transcript text must be chunked before embedding.
- Each chunk must include source metadata:
  - Session ID.
  - Video ID.
  - Platform.
  - Source URL.
  - Chunk index.
  - Start timestamp.
  - End timestamp.
  - Creator.
- Embeddings must be stored in Qdrant.
- Retrieval must filter by session ID so answers only use the two videos being compared.
- Retrieval should combine semantic transcript matches with structured metadata inserted into the prompt.

### Chat and Memory

- Each comparison session must maintain chat history.
- The graph must include prior turns when answering follow-up questions.
- Memory should be scoped to a session.
- The assistant must cite retrieved evidence and identify which video each citation came from.
- The assistant must avoid claims unsupported by transcript or metadata.

### Streaming

- The backend must stream responses to the frontend.
- Server-Sent Events are preferred for MVP because chat output is one-way from server to client.
- Each stream should support:
  - Token deltas.
  - Citation metadata.
  - Completion event.
  - Error event.

### Frontend

- React JavaScript frontend.
- Page should include:
  - Two URL inputs.
  - Analyze action.
  - Extraction progress/status.
  - Side-by-side video summary cards.
  - Engagement rate comparison.
  - Chat panel.
  - Streaming answer display.
  - Citation list with source video and timestamp where possible.
- The UI must distinguish loading, partial extraction, failed extraction, and ready states.

### Backend API

Minimum API surface:

```http
POST /api/comparisons
GET /api/comparisons/{comparison_id}
POST /api/comparisons/{comparison_id}/chat/stream
GET /api/health
```

Optional production APIs:

```http
GET /api/comparisons/{comparison_id}/events
POST /api/videos/reprocess
GET /api/videos/{video_id}
```

## 5. Non-Functional Requirements

### Reliability

- Extraction failures for one platform should not crash the whole application.
- Partial results must be preserved.
- Long-running extraction should be resumable or retryable.

### Performance

- MVP target: comparison ready within 30-120 seconds for typical short videos with captions.
- Chat response should start streaming within 2-5 seconds after retrieval.
- Retrieval should return under 500 ms for session-scoped searches at MVP scale.

### Security

- API keys must never be exposed to the frontend.
- Store secrets in environment variables or a managed secret store.
- Validate URLs to reduce SSRF risk.
- Restrict media download destinations and file sizes.
- Do not store Instagram cookies in source control.

### Observability

- Log extraction stages, provider latency, token usage, embedding count, and retrieval latency.
- Track errors by platform and provider.
- Capture formula version and extraction source for auditability.

### Compliance and Platform Risk

- YouTube and Instagram extraction can be limited by platform terms, rate limits, login requirements, or anti-bot controls.
- The product should be designed so extractor implementations are replaceable.
- For production, prefer official APIs or user-authorized data access where feasible.

## 6. Acceptance Criteria

- User submits one YouTube URL and one Instagram Reel URL.
- Backend validates both URLs.
- System extracts available metadata and transcript data.
- Engagement rate is calculated for both videos when possible.
- Transcript chunks are embedded and written to Qdrant.
- Structured records are written to MongoDB.
- User can ask a comparison question.
- GPT-4o-mini response streams to the frontend.
- Response includes citations tied to transcript chunks or metadata sources.
- Follow-up questions use session memory.
