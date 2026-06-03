# Testing

The ClipIQ frontend should be tested around the real user workflow: create comparison, process videos, review metrics, chat with citations, and handle failure states.

## Testing Strategy

Testing should cover:

- URL validation
- API normalization
- Engagement formatting
- Comparison status rendering
- Streaming event parsing
- Chat message lifecycle
- Citation rendering
- Mobile responsiveness
- Partial and failed states

## Unit Test Targets

| Area | Test |
|---|---|
| URL validation | Accept YouTube video URLs |
| URL validation | Accept Instagram Reel URLs |
| URL validation | Reject TikTok URLs |
| URL validation | Reject Instagram post URLs |
| URL validation | Reject missing URL |
| Engagement | Calculate engagement rate |
| Engagement | Return unavailable when views are zero |
| Formatters | Format counts: 120000 to 120K |
| Status mapping | Map ready/partial/failed to UI states |
| SSE parser | Parse metadata event |
| SSE parser | Parse delta event |
| SSE parser | Parse citation event |
| SSE parser | Parse done event |
| SSE parser | Parse error event |

## Manual QA Scenarios

### Create Comparison

- Open `/`.
- Confirm backend health badge appears.
- Submit empty form.
- Confirm validation errors.
- Submit two YouTube URLs.
- Confirm validation error.
- Submit YouTube + Instagram Reel.
- Confirm submit loading state.
- Confirm navigation to comparison detail page.

### Processing State

- Confirm checklist renders.
- Confirm submitted URL previews render.
- Confirm duplicate submission is disabled.
- Confirm progress does not claim completed steps without backend state.

### Ready State

- Confirm Video A is YouTube.
- Confirm Video B is Instagram.
- Confirm metrics render.
- Confirm engagement rate renders.
- Confirm unavailable fields are handled.
- Confirm chat panel is visible.
- Confirm suggested questions render.

### Streaming Chat

Ask:

```text
Why did Video A get more engagement than Video B?
```

Verify:

- User message appears.
- Assistant pending state appears.
- Text streams incrementally.
- Citations render under answer.
- Done state stops loading.

### Chat Memory

Ask a follow-up:

```text
What should Video B change first?
```

Verify:

- Assistant understands context.
- New answer appears under prior messages.
- Citations remain attached to the correct answer.

### Partial State

- Warning banner appears.
- Available data remains visible.
- Missing fields show unavailable state.
- Chat indicates when answers may be metadata-only.
- Retry extraction action is visible.

### Failed State

- Failure reason appears.
- Failed URL cards appear.
- Retry action appears.
- Start new comparison action appears.
- Technical details accordion works if available.

### History

- Recent comparisons render.
- Search filters list.
- Open report navigates to detail page.
- Failed comparison has retry action.
- Empty state renders when no history exists.

## Responsive QA

| Viewport | Requirement |
|---|---|
| 360x884 | No horizontal overflow, bottom nav usable |
| 768px width | Tablet layout remains readable |
| 1440px width | Desktop analysis + chat layout uses space well |

## Accessibility QA

- Inputs have labels.
- Buttons have accessible names.
- Form submits with keyboard.
- Focus state is visible.
- Chat streaming status uses an accessible live region.
- Error messages are readable.
- Color is not the only indicator of state.

## Backend Integration QA

Verify against:

- `GET /api/health`
- `POST /api/comparisons`
- `GET /api/comparisons/{comparison_id}`
- `POST /api/chat`
- `POST /api/comparisons/{comparison_id}/chat/stream`

## Final Demo Checklist

- Create comparison works.
- Ready state works.
- Partial state works.
- Failed state works.
- Chat streams.
- Citations render.
- Memory follow-up works.
- Reload comparison page works.
- Mobile layout works.
- No console errors.
- No fake data.
