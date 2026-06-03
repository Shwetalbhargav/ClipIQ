# Performance

ClipIQ prioritizes speed, responsiveness, and truthful UI feedback over decorative effects.

## Performance Goals

- Fast initial load.
- Smooth streaming chat.
- No layout shift when data loads.
- No fake progress.
- No unnecessary heavy libraries.
- Clean mobile performance.
- Stable UI during slow backend operations.

## Initial Load

Recommendations:

- Use Vite for fast builds and development.
- Keep dependencies minimal.
- Avoid heavy charting or video player libraries unless required.
- Use native image/video elements where possible.
- Lazy-load non-critical screens if the app grows.

## Rendering Strategy

The comparison page can contain many data fields, chat messages, citations, and status indicators.

Rules:

- Normalize data once at the API layer.
- Avoid recomputing formatted values on every render.
- Use stable component boundaries.
- Update only the active assistant message during streaming.
- Keep video cards and metric rows stable even when values are unavailable.

## Layout Stability

The UI should not jump when data arrives.

Use fixed or predictable dimensions for:

- Video thumbnails
- Video cards
- Status badges
- Buttons
- Chat input
- Bottom navigation
- Skeleton rows
- Citation cards

Unavailable values should occupy the same visual space as available values.

## Streaming Chat

Streaming is one of the most important perceived-performance moments.

The frontend should:

- Show a pending assistant state immediately.
- Append token deltas incrementally.
- Avoid re-rendering unrelated page sections on every delta.
- Disable duplicate sends while streaming.
- Show a retryable error state if the stream fails.
- Keep citations attached to the correct assistant message.

## Polling

Comparison polling should be controlled.

Recommendations:

- Poll while processing.
- Use a reasonable interval or backoff.
- Stop polling on terminal statuses.
- Stop or slow polling when the page is hidden.
- Avoid multiple overlapping requests.

Terminal statuses:

- `ready`
- `partial`
- `failed`

## Images

Video thumbnails and avatar-style images should be efficient.

Rules:

- Use `loading="lazy"` where appropriate.
- Use stable aspect ratios.
- Use object-fit cover.
- Provide broken-image fallbacks.
- Do not let missing thumbnails break layout.

## CSS and Visual Effects

Allowed:

- Subtle technical grid
- Low-cost hover states
- Border-based depth
- Small status glow for active AI/process states

Avoid:

- Heavy blur layers
- Large animated gradients
- Expensive decorative effects
- Infinite animations outside active processing states

## Mobile Performance

Mobile is a core demo target.

Requirements:

- No horizontal overflow at 360px width.
- Bottom nav must not cover controls.
- Chat input must remain usable.
- Cards should stack cleanly.
- Touch targets should be large enough.
- Avoid dense desktop-only tables on narrow screens.

## Error Performance

Error states should be fast and clear.

Examples:

- Backend offline should show quickly.
- Invalid URL should validate before submission.
- Missing metrics should not trigger repeated retries.
- Stream failure should stop loading indicators.

## Performance Checklist

- App loads quickly in development.
- No console errors.
- No visible layout shift during loading.
- Streaming answer appears incrementally.
- No duplicate chat sends.
- No broken image layout.
- Mobile layout has no horizontal scroll.
- Build completes successfully.
