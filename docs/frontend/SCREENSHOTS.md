# Screenshots

This document tracks the key ClipIQ frontend screens for demo, recruiter review, and submission materials.

## Screenshot Guidelines

Each screenshot should show a meaningful product state, not just an empty shell.

Recommended format:

```text
docs/screenshots/{screen-name}-{viewport}.png
```

Example:

```text
docs/screenshots/create-comparison-mobile.png
docs/screenshots/comparison-ready-desktop.png
```

## Required Screenshots

| Screenshot | Purpose |
|---|---|
| Create comparison | Shows URL input workflow |
| Analyzing videos | Shows extraction/chunking/indexing lifecycle |
| Ready comparison | Shows side-by-side analytics and chat |
| Streaming chat | Shows source-cited RAG response |
| Partial comparison | Shows resilient partial success UX |
| Failed comparison | Shows clear failure handling |
| History | Shows recent comparison management |
| Mobile view | Proves responsive quality |
| Desktop view | Proves analysis workspace quality |

## 1. Create Comparison

Expected content:

- ClipIQ header
- Backend health badge
- YouTube URL input
- Instagram Reel URL input
- Analyze CTA
- Feature tiles
- Mobile bottom nav when captured on mobile

Caption:

```text
Create comparison screen requiring one YouTube video and one Instagram Reel.
```

## 2. Analyzing Videos

Expected content:

- Processing progress
- Checklist
- Current active step
- Submitted URL previews
- Cancel action

Caption:

```text
Processing lifecycle for metadata, transcripts, embeddings, and RAG preparation.
```

## 3. Ready Comparison

Expected content:

- Status row
- Engagement summary
- Video A card
- Video B card
- Metrics
- Chat panel

Caption:

```text
Ready comparison report with side-by-side video analytics and source-cited AI chat.
```

## 4. Streaming Chat

Expected content:

- User question
- Assistant response
- Streaming or completed answer
- Citation cards

Caption:

```text
RAG assistant answer with transcript chunk citations.
```

## 5. Partial Comparison

Expected content:

- Partial success warning
- Available video data
- Unavailable values
- Retry extraction action
- Metadata-only assistant caveat

Caption:

```text
Partial result state when some transcript or metadata extraction failed.
```

## 6. Failed Comparison

Expected content:

- Failure message
- Potential reasons
- Failed URL cards
- Retry CTA
- Start new comparison CTA
- Optional technical details

Caption:

```text
Failure state with clear recovery actions and extraction details.
```

## 7. History

Expected content:

- Recent comparisons
- Search input
- Ready row
- Failed row
- Open/retry actions

Caption:

```text
Recent comparisons dashboard for reopening and retrying sessions.
```

## Recruiter Notes

Screenshots should communicate:

- The product problem is clear.
- The UI handles real-world failure.
- The frontend is integrated with backend/RAG concepts.
- The app is polished on mobile and desktop.
- The project is more than a static landing page.
