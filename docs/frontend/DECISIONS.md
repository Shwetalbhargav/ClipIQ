# Frontend Decisions

This document records important frontend decisions for ClipIQ.

## Decision 1: React + Vite

Use React with Vite for the frontend.

Why:

- Fast development server.
- Simple project setup.
- Strong ecosystem.
- Easy recruiter familiarity.
- Works well with Tailwind and React Router.

Tradeoff:

- Vite is frontend-focused, so backend integration must be configured through environment variables and CORS.

## Decision 2: Tailwind CSS

Use Tailwind CSS for styling.

Why:

- Fast implementation.
- Easy translation from Stitch HTML references.
- Strong responsive utilities.
- Good fit for a technical dashboard UI.
- Keeps component styles close to markup.

Tradeoff:

- Requires discipline to avoid messy duplicated class strings.

Mitigation:

- Centralize reusable primitives such as Button, Card, StatusBadge, and UnavailableValue.

## Decision 3: Rebuild Stitch Designs, Do Not Paste HTML

Use Google Stitch PNG/HTML as visual references only.

Why:

- Exported HTML is useful for tokens and layout inspiration.
- Production React components need maintainable structure.
- Blindly pasted HTML would make API integration and state handling harder.

Tradeoff:

- Rebuilding takes longer than pasting.

Benefit:

- Cleaner components, better recruiter signal, and easier future maintenance.

## Decision 4: API Normalization Layer

Normalize backend responses inside `src/api`.

Why:

- Backend payloads may evolve.
- UI components should stay simple.
- Missing values can be handled consistently.
- Prevents `null`, `undefined`, or `NaN` leaks.

Benefit:

- More resilient frontend.

## Decision 5: Server-Sent Events with Fetch

Consume streaming chat using `fetch` and `ReadableStream`.

Why:

- The backend streaming endpoint is a `POST`.
- Native `EventSource` is designed around `GET`.
- `fetch` supports JSON request bodies and stream parsing.

Tradeoff:

- SSE parsing must be implemented carefully.

Benefit:

- Supports real streaming chat with request payloads.

## Decision 6: Session-Scoped Chat Memory

Chat memory is scoped to `comparison_id`.

Why:

- Each comparison has its own transcript chunks and metadata.
- Follow-up questions should refer only to the active comparison.
- Avoids cross-session leakage.

Tradeoff:

- Global user memory is not part of the MVP.

## Decision 7: Truthful Unavailable States

Show unavailable values instead of placeholders or fabricated values.

Why:

- Social platform extraction can fail.
- Metrics may be missing.
- Transcript access can be blocked.
- Trust is more important than visual completeness.

Examples:

- Missing views: engagement rate unavailable.
- Missing transcript: transcript unavailable badge.
- Missing citations: no citations returned warning.

## Decision 8: Partial and Failed States Are First-Class

Build partial and failed comparison screens as intentional product states.

Why:

- Instagram and social extraction can fail in real demos.
- A polished failure state shows engineering maturity.
- Recruiters and reviewers value resilient UX.

Benefit:

- The app looks production-ready instead of brittle.

## Decision 9: Mobile-First Demo Quality

Treat mobile as a core viewport.

Why:

- The design references are strongly mobile-oriented.
- Social video creators are mobile-heavy users.
- Recruiter demos often happen on narrow preview panes.

Requirements:

- No horizontal overflow.
- Bottom nav does not cover inputs.
- Chat remains usable.
- Video cards stack cleanly.

## Decision 10: Minimal Heavy Dependencies

Avoid heavy charting/video/player libraries in the MVP unless needed.

Why:

- Performance is a stated requirement.
- The product is metric and chat driven.
- Native elements and simple cards are enough for the first version.

Benefit:

- Faster load.
- Less bundle weight.
- Fewer integration risks.
