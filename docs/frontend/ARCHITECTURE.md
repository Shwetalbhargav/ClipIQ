# Frontend Architecture

The ClipIQ frontend is organized around a clear separation between API normalization, page-level orchestration, reusable UI components, and feature-specific components.

## Architecture Goals

- Keep backend payload complexity out of UI components.
- Make every comparison state render safely.
- Support streaming chat without re-rendering the entire page on every token.
- Keep mobile and desktop layouts first-class.
- Make the project easy for another engineer or recruiter to understand quickly.

## High-Level Flow

```text
User enters URLs
        |
        v
CreateComparisonPage
        |
        v
POST /api/comparisons
        |
        v
Navigate to /comparisons/:comparisonId
        |
        v
ComparisonPage loads GET /api/comparisons/:id
        |
        +--> processing UI
        +--> ready UI
        +--> partial UI
        +--> failed UI
        |
        v
ChatPanel streams from /api/comparisons/:id/chat/stream
```

## Folder Structure

```text
frontend/
|-- src/
|   |-- api/
|   |-- components/
|   |-- hooks/
|   |-- pages/
|   |-- routes/
|   |-- utils/
|   |-- constants/
|   `-- styles/
```

## API Layer

The `src/api` folder owns backend communication and response normalization.

| File | Responsibility |
|---|---|
| `client.js` | Base URL, shared request helpers, error normalization |
| `health.js` | Health check API |
| `comparisons.js` | Create/get comparison helpers |
| `streamChat.js` | SSE stream parser for chat responses |

UI components should not depend on raw backend payloads. The API layer should normalize backend responses into frontend-friendly shapes.

## Page Layer

| Page | Responsibility |
|---|---|
| `CreateComparisonPage.jsx` | URL form, validation, health badge, submit flow |
| `ComparisonPage.jsx` | Loads comparison by ID and chooses processing/ready/partial/failed UI |
| `HistoryPage.jsx` | Shows recent sessions from backend or localStorage fallback |
| `NotFoundPage.jsx` | Handles unknown routes |

## Component Layer

### Layout Components

- `AppShell`
- `Header`
- `Sidebar`
- `BottomNav`
- `PageContainer`

### Comparison Components

- `AnalysisLoadingState`
- `LoadingChecklist`
- `SubmittedUrlPreview`
- `ComparisonStatusBar`
- `EngagementSummary`
- `VideoCard`
- `MetricRow`
- `PartialWarning`
- `FailedComparisonState`

### Chat Components

- `ChatPanel`
- `ChatMessage`
- `ChatInput`
- `SuggestedQuestions`
- `StreamingIndicator`

### Citation Components

- `CitationList`
- `CitationCard`
- `TimestampRange`

Citations should show video label, platform, chunk index, timestamp range, and transcript excerpt.

## State Management

ClipIQ can use React state and custom hooks for the MVP.

| Hook | Purpose |
|---|---|
| `useHealth` | Backend readiness |
| `useComparison` | Fetch, poll, and normalize comparison state |
| `useStreamingChat` | Manage active streaming message lifecycle |
| `useLocalHistory` | Store recent comparison sessions locally |

## Comparison State Machine

```text
idle
 |
submitting
 |
processing
 |----> ready
 |----> partial
 |----> failed
 |
error
```

Supported backend statuses:

- `ready`
- `partial`
- `failed`

The UI may also use local-only states:

- `idle`
- `submitting`
- `loading`
- `offline`

## Streaming Chat Architecture

Streaming chat uses `fetch` with a readable response stream because the endpoint is a `POST` request with a JSON body.

| Event | UI Behavior |
|---|---|
| `metadata` | Create assistant response shell |
| `delta` | Append text to active assistant message |
| `citation` | Attach citation to active assistant message |
| `done` | Mark assistant message complete |
| `error` | Mark assistant message failed and show retry |

## Error Handling

| Backend/Error State | Frontend Display |
|---|---|
| `422` invalid URL | Inline form validation |
| `404` comparison missing | Not found state |
| `503` service unavailable | Backend offline/service unavailable banner |
| Stream error event | Retryable chat message error |
| Missing metric | `Unavailable` value |
| Missing transcript | Transcript unavailable badge |

## Architecture Principles

- Normalize once, render many times.
- Prefer truthful unavailable states over placeholders.
- Make partial success feel intentional.
- Keep performance-sensitive streaming logic isolated.
- Keep design tokens centralized.
- Avoid duplicated formatting logic across components.
