# ClipIQ Backend API Contract

Base URL for local development:

```text
http://localhost:8000
```

## 1. Health Check

```http
GET /api/health
```

Checks whether the backend can reach MongoDB and Qdrant.

### Expected Response

```json
{
  "status": "ok",
  "service": "ClipIQ",
  "environment": "development",
  "services": {
    "mongodb": "ok",
    "qdrant": "ok"
  }
}
```

### Acceptance Criteria

- Returns HTTP `200`.
- Returns `status`.
- Returns MongoDB and Qdrant health under `services`.
- Frontend can use this for basic readiness checks.

## 2. Create Comparison

```http
POST /api/comparisons
```

Creates a comparison/session from exactly one YouTube URL and exactly one Instagram Reel URL. This is the main demo setup endpoint.

### Request Body

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "instagram_url": "https://www.instagram.com/reel/REEL_ID/"
}
```

### Expected Response

```json
{
  "comparison_id": "uuid",
  "status": "ready",
  "video_a": {
    "label": "A",
    "platform": "youtube",
    "creator": "Creator name",
    "follower_count": 100000,
    "views": 10000,
    "likes": 800,
    "comments": 200,
    "engagement_rate": 10.0,
    "transcript_status": "ready",
    "chunk_count": 3,
    "indexed_chunk_count": 3
  },
  "video_b": {
    "label": "B",
    "platform": "instagram",
    "creator": "Creator name",
    "follower_count": 50000,
    "views": 5000,
    "likes": 250,
    "comments": 50,
    "engagement_rate": 6.0,
    "transcript_status": "ready",
    "chunk_count": 2,
    "indexed_chunk_count": 2
  },
  "transcript_status": {
    "A": "ready",
    "B": "ready"
  },
  "indexing_status": {
    "A": "indexed",
    "B": "indexed"
  },
  "engagement": {
    "summary": "Video A engagement is 10.0%; Video B engagement is 6.0%."
  },
  "errors": []
}
```

### Status Values

- `ready`: both videos were processed and indexed.
- `partial`: at least one step failed or transcript/indexing is incomplete.
- `failed`: no usable comparison could be created.

### Acceptance Criteria

- Requires `youtube_url`.
- Requires `instagram_url`.
- Rejects one URL only with HTTP `422`.
- Rejects two YouTube URLs with HTTP `422`.
- Rejects TikTok/unsupported URLs with HTTP `422`.
- Rejects Instagram posts like `/p/...`; only `/reel/...` or `/reels/...` are valid.
- Maps YouTube to `video_a`.
- Maps Instagram Reel to `video_b`.
- Returns a `comparison_id`.
- Returns `engagement_rate` as `null` when metrics are missing or views are zero.
- Does not fabricate missing views, likes, comments, followers, or transcript data.
- Returns `partial` instead of crashing when one extraction step fails.
- Persists comparison data so `GET /api/comparisons/{comparison_id}` can retrieve it.

## 3. Get Comparison

```http
GET /api/comparisons/{comparison_id}
```

Fetches a previously created comparison/session.

### Expected Response

Same shape as `POST /api/comparisons`.

### Acceptance Criteria

- Returns HTTP `200` for an existing `comparison_id`.
- Returns HTTP `404` for a missing comparison.
- Returns `video_a` and `video_b` when available.
- Returns persisted engagement metrics.
- Returns transcript/indexing status from stored records.
- Frontend can safely reload a comparison page using this endpoint.

## 4. Non-Streaming Chat

```http
POST /api/chat
```

Runs a RAG chat turn and returns the full answer at once.

### Request Body

```json
{
  "session_id": "comparison_id_here",
  "message": "Why did Video A get more engagement than Video B?",
  "top_k": 8
}
```

### Expected Response

```json
{
  "response_id": "uuid",
  "session_id": "comparison_id_here",
  "answer": "Video A likely performed better because...",
  "citations": [
    {
      "label": "Video A Chunk 0",
      "video_id": "A",
      "chunk_id": "chunk-id",
      "chunk_index": 0,
      "platform": "youtube",
      "start_seconds": 0,
      "end_seconds": 5,
      "text": "Transcript excerpt..."
    }
  ],
  "model": "gpt-4o-mini",
  "usage": {}
}
```

### Acceptance Criteria

- Requires `session_id`.
- Requires non-empty `message`.
- Uses only sources from the requested comparison/session.
- Returns citations for retrieved transcript chunks.
- Maintains conversation memory across turns.
- Returns HTTP `404` if the session is missing or not ready.
- Returns HTTP `503` if the chat service is not configured.

## 5. Streaming Chat

```http
POST /api/comparisons/{comparison_id}/chat/stream
```

Streams a RAG chat response with Server-Sent Events.

### Request Body

```json
{
  "message": "Compare the hooks in the first 5 seconds.",
  "user_id": "optional-user-id"
}
```

### Event Types

#### metadata

Sent first.

```json
{
  "type": "metadata",
  "response_id": "resp_x",
  "comparison_id": "comparison_id_here",
  "model": "gpt-4o-mini",
  "started_at": "2026-06-03T00:00:00Z"
}
```

#### delta

Sent repeatedly as model text streams.

```json
{
  "type": "delta",
  "text": "Video "
}
```

#### citation

Sent for cited source chunks.

```json
{
  "type": "citation",
  "label": "Video A Chunk 0",
  "video_id": "A",
  "chunk_index": 0,
  "text": "Transcript excerpt..."
}
```

#### done

Sent when the response is complete.

```json
{
  "type": "done",
  "response_id": "resp_x",
  "status": "completed",
  "usage": {
    "streamed_delta_count": 42,
    "citation_count": 2
  }
}
```

#### error

Sent when streaming fails.

```json
{
  "type": "error",
  "status": "failed",
  "error": {
    "code": "stream_failed",
    "message": "The response stream failed before completion. Please retry."
  }
}
```

### Acceptance Criteria

- Returns `text/event-stream`.
- Emits `metadata` before answer deltas.
- Emits real streamed model token deltas, not only a completed answer.
- Emits citations when transcript chunks are used.
- Emits `done` at the end.
- Emits safe `error` events without leaking stack traces or secrets.
- Stops cleanly when the client disconnects.
- Maintains memory across streamed turns.

## 6. Legacy Metadata Analyze

```http
POST /api/videos/analyze
```

Metadata-only endpoint. The frontend should prefer `POST /api/comparisons` for the full product flow.

### Request Body

```json
{
  "urls": [
    "https://www.youtube.com/watch?v=VIDEO_ID",
    "https://www.instagram.com/reel/REEL_ID/"
  ]
}
```

### Acceptance Criteria

- Requires exactly two URLs.
- Requires one YouTube URL and one Instagram Reel URL.
- Returns normalized metadata only.
- Does not prepare transcript chunks, embeddings, Qdrant index, or chat session.

## Frontend QA Checklist

- User can submit one YouTube URL and one Instagram Reel URL.
- Frontend shows loading state while `POST /api/comparisons` runs.
- Frontend handles `ready`, `partial`, and `failed`.
- Frontend displays side-by-side video cards for Video A and Video B.
- Frontend displays engagement rates and `null`/unavailable values honestly.
- Chat panel uses `comparison_id`.
- Streaming chat appends `delta.text` incrementally.
- Citations are shown with video label and chunk index.
- Chat memory works across follow-up questions.
- Errors are visible but not noisy.
- Page can reload using `GET /api/comparisons/{comparison_id}`.
