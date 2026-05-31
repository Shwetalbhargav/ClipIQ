# Costing and Scaling

## 1. Cost Drivers

The main cost drivers are:

- LLM tokens for GPT-4o-mini chat responses.
- Embedding tokens for transcript chunks.
- Speech-to-text fallback when captions are unavailable.
- Video extraction bandwidth and compute.
- MongoDB storage and compute.
- Qdrant storage and compute.
- Background worker capacity.
- Observability and logs.

The cheapest path is caption-first extraction, small chunks, scoped retrieval, GPT-4o-mini streaming, and caching by normalized video URL.

## 2. MVP Cost Profile

Assumptions:

- Two short videos per comparison.
- Captions available for most YouTube videos.
- Instagram transcript availability is inconsistent.
- Average transcript length: 1,000-3,000 words per video.
- 10-30 transcript chunks per comparison.
- 3-10 chat questions per comparison.

Expected cost shape:

- Embeddings: low per comparison.
- GPT-4o-mini chat: low to moderate depending on prompt size and answer length.
- Transcription: can dominate cost when fallback is used.
- Infrastructure: low if Qdrant and MongoDB are small managed instances or local services.

## 3. Scaling Target: 1,000 Creators per Day

If each creator runs one comparison per day:

- 1,000 comparisons/day.
- 2,000 videos/day submitted.
- 20,000-60,000 chunks/day at 10-30 chunks per comparison.
- 3,000-10,000 chat turns/day at 3-10 questions per comparison.

The system can support this with:

- Background extraction workers.
- Idempotent video cache.
- Queue-based rate limiting.
- Managed MongoDB.
- Managed or clustered Qdrant.
- Provider usage budgets and per-user quotas.

## 4. Scaling Architecture

MVP request-time flow is acceptable for demos but not for production. Production should split work:

```text
API service
  -> creates comparison and jobs
  -> returns comparison ID

Worker service
  -> extracts metadata/transcripts
  -> computes metrics
  -> chunks and embeds
  -> writes MongoDB and Qdrant

Chat service
  -> streams LangGraph + GPT-4o-mini answers
```

Benefits:

- API remains responsive.
- Failed extraction jobs can retry safely.
- Worker concurrency can scale independently.
- Transcription can be isolated from chat traffic.

## 5. Caching Strategy

Cache by normalized platform video ID:

- Metadata snapshot.
- Transcript segments.
- Chunks.
- Embeddings.
- Thumbnail URL.
- Extraction errors.

Use cache invalidation rules:

- Metadata can refresh because views/likes/comments change.
- Transcript rarely changes after publication.
- Embeddings only need recompute when chunking or embedding model changes.

Recommended TTL:

- Metrics: 6-24 hours.
- Transcript: 30+ days or permanent with versioning.
- Failed extraction: short TTL, such as 1-6 hours.

Tradeoff:

- Aggressive caching lowers cost and latency but may show stale engagement metrics.
- Fresh extraction improves accuracy but increases rate-limit and cost pressure.

## 6. Qdrant Scaling

For 1,000 comparisons/day, Qdrant load is modest if chunks are short-form video transcripts. Important practices:

- Use payload indexes on `comparison_id`, `video_id`, and `platform`.
- Filter every retrieval by comparison ID.
- Store compact payloads; keep full canonical records in MongoDB.
- Use deterministic point IDs for idempotent reindexing.
- Monitor collection size, query latency, and failed writes.

Scaling options:

- Local Docker Qdrant for development.
- Managed Qdrant for production simplicity.
- Clustered self-hosted Qdrant when cost control and infrastructure maturity justify it.

## 7. MongoDB Scaling

MongoDB will store more operational data than Qdrant:

- comparisons
- videos
- metrics snapshots
- transcript segments
- chat history
- citations
- jobs

Recommended practices:

- Add indexes on `comparison_id`, `video_id`, `creator`, and `created_at`.
- Archive chat/events if volume grows.
- Keep raw extractor payloads as nested documents, but promote frequently queried fields to indexed top-level fields.
- Keep application-level schema changes documented in source control.
- Use connection pooling and managed backups in production.

## 8. LLM Cost Control

Controls:

- Keep retrieval top-k small, usually 6-12 chunks.
- Trim chunk text to relevant excerpts.
- Include compact structured metadata instead of raw payloads.
- Use memory summaries for long chats.
- Cap max output tokens.
- Add user-level quotas.

Tradeoff:

- Smaller prompts reduce cost but can hurt answer quality.
- Larger prompts improve context but increase latency and spend.

Recommended default:

- Use metadata summary for both videos.
- Retrieve top 8 transcript chunks.
- Include last 6 chat turns plus a rolling memory summary.

## 9. Transcription Cost Control

Transcription is often more expensive than embeddings for this product.

Controls:

- Prefer platform captions.
- Only run speech-to-text when user asks or when transcript is required.
- Put transcription behind a feature flag in MVP.
- Cache audio-derived transcripts permanently with source/version metadata.
- Set max video duration for MVP.

Tradeoff:

- No fallback means weaker coverage.
- Automatic fallback improves UX but can produce surprise cost.

Recommended MVP:

- Caption-first.
- Manual or explicitly enabled transcription fallback.
- Clear UI when transcript is unavailable.

## 10. Operational Limits

Initial production guardrails:

- Max video duration: 10 minutes.
- Max transcript chunks per video: 100.
- Max chat turns per comparison before summarization: 12.
- Max concurrent extraction jobs per user: 2.
- Max retries per extraction job: 3.
- Provider timeout per extraction step: 60-180 seconds depending on task.

## 11. Reliability and Monitoring

Track:

- Extraction success rate by platform.
- Transcript availability rate.
- Average analysis time.
- Qdrant indexing failures.
- Retrieval latency.
- GPT first-token latency.
- Total token usage per user/comparison.
- Engagement metric availability.

Alerts:

- Extraction failure spike.
- Qdrant unavailable.
- MongoDB connection saturation.
- LLM provider errors.
- Cost anomaly by user or provider.
