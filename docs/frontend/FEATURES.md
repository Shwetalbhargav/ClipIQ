# Features

ClipIQ is a source-cited RAG comparison interface for creators analyzing why one social video performed better than another.

## 1. YouTube vs Instagram Reels Comparison

The core workflow requires exactly:

- One YouTube video URL
- One Instagram Reel URL

Rules:

- YouTube is Video A.
- Instagram Reel is Video B.
- TikTok, generic Instagram posts, playlists, channels, and missing URLs are invalid.

## 2. Metadata Extraction Display

Each video card can display:

- Platform
- Creator
- Follower count
- Title or caption
- Views
- Likes
- Comments
- Hashtags
- Upload date
- Duration
- Thumbnail
- Transcript status
- Chunk count
- Indexed chunk count

Unavailable values are shown honestly.

## 3. Engagement Rate

ClipIQ calculates engagement rate as:

```text
((likes + comments) / views) * 100
```

The frontend displays engagement rate for both videos and highlights the stronger performer when available.

If views are missing or zero, engagement rate is shown as unavailable.

## 4. Processing Lifecycle

The analyzing screen shows the full AI pipeline:

- Validating URLs
- Extracting YouTube metadata
- Extracting Instagram Reel metadata
- Pulling transcripts
- Chunking transcript text
- Embedding chunks
- Indexing vector database
- Preparing RAG chat

The UI must not fake completed backend steps.

## 5. Side-by-Side Video Cards

The comparison detail page presents both videos in a scannable layout.

Video cards include:

- Thumbnail
- Platform
- Creator
- Engagement rate
- Metrics
- Transcript/chunk status
- Duration
- Missing-data fallback states

## 6. Engagement Summary

The engagement summary explains:

- Winner
- Engagement delta
- Formula
- Short performance reason if available
- Whether transcript/indexing data is ready

## 7. Streaming RAG Chat

The chat panel lets creators ask questions about the comparison.

Required demo questions:

- Why did Video A get more engagement than Video B?
- What is the engagement rate of each?
- Compare the hooks in the first 5 seconds.
- Who is the creator of Video B and what is their follower count?
- Suggest improvements for B based on what worked in A.

Assistant answers should stream visibly.

## 8. Source Citations

Every transcript-grounded answer should include citations.

Citation cards show:

- Video A or Video B
- Platform
- Chunk index
- Timestamp range
- Transcript excerpt

Example:

```text
Video A Chunk 0 (0:00-0:05)
```

## 9. Chat Memory

Chat memory is scoped to the comparison session.

The assistant should understand follow-up questions such as:

```text
What about the second video?
```

## 10. Partial Success State

Partial success is shown when some extraction or indexing steps worked and others failed.

The UI should show:

- Warning banner
- Available video data
- Unavailable values for failed fields
- Retry extraction action
- Metadata-only chat warning when transcript chunks are missing

## 11. Failed State

Failed state is shown when no usable comparison can be created.

The UI should show:

- Clear failure message
- Potential reasons
- Failed URL cards
- Retry action
- Start new comparison action
- Optional extraction logs/details accordion

## 12. History

The history page shows recent comparison sessions.

Features:

- Search creators
- Open ready report
- Retry failed comparison
- Show ready, partial, and failed statuses
- Use localStorage fallback if backend history endpoint is unavailable

## 13. Backend Health

The create page shows backend readiness.

States:

- Backend Online
- Backend Offline
- Service Degraded

Health should not block the user from typing.

## 14. Recruiter-Visible Strengths

This frontend demonstrates:

- API integration
- Streaming AI UX
- RAG citation rendering
- State-driven UI architecture
- Responsive design
- Error handling
- Product thinking
- Performance-conscious implementation
