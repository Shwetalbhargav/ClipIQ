# ClipIQ Frontend

ClipIQ is a performance-first creator analytics frontend for comparing one YouTube video against one Instagram Reel using a source-cited RAG chatbot.

The frontend lets creators submit two social media video URLs, monitor extraction progress, compare engagement metrics, and ask an AI assistant why one video performed better than the other.

## Core Experience

- Submit exactly one YouTube video URL and one Instagram Reel URL.
- Track processing: URL validation, metadata extraction, transcript extraction, chunking, embedding, vector indexing, and RAG chat preparation.
- Compare Video A and Video B side by side.
- Display views, likes, comments, creator, follower count, hashtags, upload date, duration, transcript status, chunk count, and engagement rate.
- Chat with a streaming RAG assistant.
- View citations for each answer by video and transcript chunk.
- Handle ready, partial, failed, loading, and backend-offline states honestly.

## Tech Stack

- React
- Vite
- Tailwind CSS
- React Router
- Axios or Fetch API
- Server-Sent Events via `fetch` and `ReadableStream`
- lucide-react icons

## Product Rule

Video A is always YouTube.

Video B is always Instagram Reels.

Engagement rate:

```text
((likes + comments) / views) * 100
```

If views, likes, comments, transcript data, or creator metadata are unavailable, the UI must show an unavailable state instead of fabricating values.

## Main Routes

| Route | Purpose |
|---|---|
| `/` | Create a new comparison |
| `/comparisons/:comparisonId` | View processing, ready, partial, or failed comparison state |
| `/history` | View recent comparison sessions |
| `*` | Not found state |

## Backend API

Local backend:

```text
http://localhost:8000
```

Primary endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend, MongoDB, and Qdrant health |
| `POST` | `/api/comparisons` | Create a YouTube vs Instagram comparison |
| `GET` | `/api/comparisons/{comparison_id}` | Reload an existing comparison |
| `POST` | `/api/chat` | Non-streaming RAG chat |
| `POST` | `/api/comparisons/{comparison_id}/chat/stream` | Streaming RAG chat |

## Design Reference

The UI follows the Kinetic Logic design system:

- Dark technical SaaS interface
- Dense but readable analytics layout
- Structural borders instead of heavy shadows
- Status colors reserved for processing, success, warning, and failure
- Mobile-first comparison and chat experience

## Local Development

```bash
npm install
npm run dev
```

Expected local frontend:

```text
http://localhost:5173
```

Expected local backend:

```text
http://localhost:8000
```

## Vercel Deployment

Use the Vite preset on Vercel.

| Setting | Value |
|---|---|
| Framework preset | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| Environment variable | `VITE_API_BASE_URL` |

## Quality Bar

- No fake progress.
- No fake metrics.
- No fake citations.
- No broken image states.
- No `undefined`, `null`, or `NaN` in the UI.
- No horizontal overflow on mobile.
- Streaming chat should visibly stream, not wait and dump a full answer.
- Partial and failed states should look intentional.

## Recruiter Summary

ClipIQ demonstrates frontend engineering across product UX, API integration, streaming AI responses, state management, resilient error handling, responsive design, and polished technical documentation.
