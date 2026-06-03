# ClipIQ Design System

ClipIQ uses the Kinetic Logic design system: a dark, dense, technical SaaS interface for AI video analytics.

The design should feel precise, fast, and trustworthy. It should prioritize data clarity and processing state over decoration.

## Design Personality

- Technical
- Minimal
- Analytical
- High-density
- Calm under complex processing
- Built for creators and operators comparing performance data

## Color Tokens

| Token | Value | Usage |
|---|---:|---|
| `surface` | `#0b1326` | Main background |
| `surface-container-lowest` | `#060e20` | Deep input/background surface |
| `surface-container-low` | `#131b2e` | Low cards, nav |
| `surface-container` | `#171f33` | Primary cards |
| `surface-container-high` | `#222a3d` | Raised card headers |
| `surface-container-highest` | `#2d3449` | Active surfaces |
| `on-surface` | `#dae2fd` | Primary text |
| `on-surface-variant` | `#c2c6d6` | Secondary text |
| `outline` | `#8c909f` | Strong border |
| `outline-variant` | `#424754` | Subtle border |
| `primary` | `#adc6ff` | AI/action accent |
| `primary-container` | `#4d8eff` | Primary action fill |
| `secondary` | `#d0bcff` | Instagram/Video B accent |
| `tertiary` | `#4edea3` | Success/ready |
| `error` | `#ffb4ab` | Error/failed |
| `error-container` | `#93000a` | Error banner/card |

## Typography

| Role | Font | Size | Weight | Usage |
|---|---|---:|---:|---|
| Headline XL | Inter | 36px | 700 | Hero or major page title |
| Headline LG | Inter | 24px | 600 | Page section title |
| Headline MD | Inter | 20px | 600 | Card title |
| Body LG | Inter | 16px | 400 | Page body |
| Body MD | Inter | 14px | 400 | Default UI text |
| Body SM | Inter | 12px | 400 | Supporting text |
| Label MD | Geist | 13px | 500 | Labels, tabs, buttons |
| Mono SM | Geist | 12px | 400 | IDs, chunks, timestamps, formulas |

## Layout

### Desktop

- Fixed sidebar: 260px
- Main content: fluid, max width around 1440px
- Grid: 12-column mental model
- Main spacing: 24px
- Cards: 16px internal padding for dense data

### Mobile

- Single column
- 16px page gutter
- Bottom navigation
- Chat input must remain visible and not be covered by nav
- No horizontal overflow at 360px width

## Shape

| Element | Radius |
|---|---:|
| Buttons | 8px |
| Inputs | 8px |
| Cards | 12px to 16px |
| Badges | Full pill |
| Video thumbnails | 12px |

## Borders and Elevation

ClipIQ avoids heavy shadows.

Use:

- 1px structural borders
- tonal surface layering
- subtle active-state glow only for processing and AI-ready indicators

Avoid:

- large decorative shadows
- gradient blobs
- unnecessary glassmorphism
- excessive blur effects

## Component Rules

### Buttons

Primary buttons:

- Filled primary color
- Clear icon + text
- Stable height
- Disabled state during submission/streaming

Secondary buttons:

- Border style
- Surface hover state
- Used for retry, cancel, export, secondary actions

### Inputs

Inputs should include:

- Visible label
- Placeholder example
- Platform icon
- Focus ring
- Inline validation error
- Stable height

### Status Badges

Badges should use a dot + label pattern.

Examples:

- Backend Online
- Ready
- Partial Success
- Failed
- Transcripts Indexed
- AI Ready

### Video Cards

Each video card should show:

- Platform label
- Creator
- Thumbnail
- Duration
- Views
- Likes
- Comments
- Followers
- Engagement rate
- Transcript status
- Chunk count

Video A uses YouTube/primary accent.

Video B uses Instagram/secondary accent.

### Chat

Chat should feel like a technical assistant panel, not a generic support widget.

Assistant messages include:

- AI icon
- Streamed answer text
- Citation section
- Retry state if stream fails

### Citations

Citation cards should be compact and scannable.

Required fields:

- Video A/B
- Chunk index
- Timestamp range
- Excerpt

Example label:

```text
Video A Chunk 0 (0:00-0:05)
```

## Design Quality Rules

- Do not show app instructions as long visible copy.
- Do not hide missing data.
- Do not make the UI look successful when extraction failed.
- Do not use fake metrics.
- Do not let text overflow buttons/cards.
- Do not use tiny unreadable labels.
- Do not let mobile nav cover important controls.
