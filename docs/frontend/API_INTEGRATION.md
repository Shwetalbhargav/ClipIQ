# API Integration

The frontend integrates with the ClipIQ FastAPI backend.

Local backend:

```text
http://localhost:8000
```

API prefix:

```text
/api
```

## Health Check

```http
GET /api/health
```

Purpose:

- Confirm backend availability.
- Confirm MongoDB and Qdrant health.
- Drive the frontend health badge.

Expected response:

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

Frontend behavior:

- Show `Backend Online` when healthy.
- Show `Backend Offline` or `Service Degraded` when unavailable.
- Do not block URL input while health is pending.

## Create Comparison

```http
POST /api/comparisons
```

Request body:

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "instagram_url": "https://www.instagram.com/reel/REEL_ID/"
}
```

Important rules:

- `youtube_url` must be a supported YouTube video URL.
- `instagram_url` must be an Instagram Reel URL.
- Instagram posts such as `/p/...` are invalid.
- TikTok and other unsupported sources are invalid.
- YouTube always maps to `video_a`.
- Instagram always maps to `video_b`.

Expected response shape:

```json
{
  "comparison_id": "uuid",
  "status": "ready",
  "video_a": {
    "label": "A",
    "video_id": "id",
    "platform": "youtube",
    "source_url": "url",
    "canonical_url": "url",
    "creator": "Creator",
    "follower_count": 100000,
    "title": "Video title",
    "caption": null,
    "views": 10000,
    "likes": 800,
    "comments": 200,
    "engagement_rate": 10.0,
    "hashtags": [],
    "upload_date": "2026-06-03T00:00:00Z",
    "duration_seconds": 120,
    "thumbnail_url": "url",
    "transcript_status": "ready",
    "chunk_count": 3,
    "indexed_chunk_count": 3
  },
  "video_b": {
    "label": "B",
    "video_id": "id",
    "platform": "instagram",
    "source_url": "url",
    "canonical_url": "url",
    "creator": "Creator",
    "follower_count": 50000,
    "title": null,
    "caption": "Caption text",
    "views": 5000,
    "likes": 250,
    "comments": 50,
    "engagement_rate": 6.0,
    "hashtags": [],
    "upload_date": "2026-06-03T00:00:00Z",
    "duration_seconds": 60,
    "thumbnail_url": "url",
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
  "errors": [],
  "created_at": "2026-06-03T00:00:00Z",
  "updated_at": "2026-06-03T00:00:00Z"
}
```

Supported statuses:

| Status | Meaning |
|---|---|
| `ready` | Both videos processed and indexed |
| `partial` | At least one step failed or is incomplete |
| `failed` | No usable comparison could be created |

Frontend behavior:

- Navigate to `/comparisons/{comparison_id}` after success.
- Render ready/partial/failed UI based on `status`.
- Store minimal recent session data in local history.
- Never fabricate missing fields.

## Get Comparison

```http
GET /api/comparisons/{comparison_id}
```

Purpose:

Reload a persisted comparison session.

Frontend behavior:

- Use on direct page load.
- Show not found state on `404`.
- Stop polling on terminal statuses: `ready`, `partial`, `failed`.

## Non-Streaming Chat

```http
POST /api/chat
```

Request body:

```json
{
  "session_id": "comparison_id",
  "message": "Why did Video A get more engagement than Video B?",
  "top_k": 8
}
```

Frontend behavior:

- Use as fallback if streaming is unavailable.
- Still render citations.
- Preserve session-specific chat history.

## Streaming Chat

```http
POST /api/comparisons/{comparison_id}/chat/stream
```

Request body:

```json
{
  "message": "Compare the hooks in the first 5 seconds.",
  "user_id": "optional-user-id"
}
```

Expected content type:

```text
text/event-stream
```

Event types:

| Event | Purpose |
|---|---|
| `metadata` | Response/model/session metadata |
| `delta` | Incremental assistant text |
| `citation` | Source chunk evidence |
| `done` | Stream complete |
| `error` | Safe stream failure |

Frontend behavior:

- Create an assistant message shell on `metadata`.
- Append `delta.text` to the active assistant message.
- Attach `citation` events to the active message.
- Mark complete on `done`.
- Show retryable error on `error`.
- Prevent duplicate sends while one message is streaming.

## Error Handling

| Status/Event | Frontend Behavior |
|---|---|
| `422` | Show form validation error |
| `404` | Show comparison not found |
| `503` | Show backend/service unavailable |
| stream `error` | Show retryable chat error |
| missing metric | Show `Unavailable` |
| missing transcript | Show transcript unavailable badge |
| missing citation | Show no citations warning |

## API Integration Principles

- Keep raw response mapping inside `src/api`.
- Components should receive normalized values.
- Missing data should never leak as `null`, `undefined`, or `NaN`.
- API errors should become readable UI states.
- Chat memory is scoped to `comparison_id`.
