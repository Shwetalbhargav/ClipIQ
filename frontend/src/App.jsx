import { Activity, Bot, Database, FileText, Film, Radio, Sparkles } from 'lucide-react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'

const featureCards = [
  {
    title: 'Transcript RAG',
    description: 'Chunked transcripts, vector search, and source-grounded answers.',
    icon: FileText,
  },
  {
    title: 'Engagement Metrics',
    description: 'Creator, views, likes, comments, followers, and honest unavailable states.',
    icon: Activity,
  },
  {
    title: 'Streaming Chat',
    description: 'Readable AI responses that stream with citations and session memory.',
    icon: Bot,
  },
  {
    title: 'Vector Index',
    description: 'Chunk metadata is scoped by comparison and video labels A/B.',
    icon: Database,
  },
]

function Header() {
  return (
    <header className="border-outline-variant bg-surface/95 sticky top-0 z-20 border-b backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-3" aria-label="ClipIQ home">
          <span className="border-primary/50 bg-surface-container flex h-9 w-9 items-center justify-center rounded-lg border">
            <Activity className="text-primary h-5 w-5" aria-hidden="true" />
          </span>
          <span className="text-on-surface text-xl font-bold tracking-tight">ClipIQ</span>
        </Link>
        <div className="border-tertiary/25 bg-tertiary/10 text-tertiary flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider">
          <span className="bg-tertiary h-2 w-2 rounded-full" />
          Vercel Ready
        </div>
      </div>
    </header>
  )
}

function CreateComparisonPage() {
  return (
    <main className="mx-auto grid min-h-[calc(100vh-64px)] max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1fr_440px] lg:items-center">
      <section className="space-y-8">
        <div className="max-w-3xl space-y-5">
          <p className="text-primary font-semibold uppercase tracking-[0.3em]">Creator RAG Analytics</p>
          <h1 className="text-on-surface text-4xl font-black leading-tight sm:text-6xl">
            Compare YouTube vs Instagram Reels with source-cited AI.
          </h1>
          <p className="text-on-surface-variant max-w-2xl text-lg">
            Frontend foundation for ClipIQ: mandatory two-platform input, side-by-side video cards,
            engagement metrics, streaming chat, citations, and resilient partial or failed states.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {featureCards.map(({ title, description, icon: Icon }) => (
            <article key={title} className="border-outline-variant bg-surface-container-low rounded-xl border p-5">
              <div className="bg-surface-container-highest mb-4 flex h-11 w-11 items-center justify-center rounded-lg">
                <Icon className="text-primary h-5 w-5" aria-hidden="true" />
              </div>
              <h2 className="text-on-surface font-semibold">{title}</h2>
              <p className="text-on-surface-variant mt-2 text-sm leading-6">{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-outline-variant bg-surface-container rounded-2xl border p-6 shadow-2xl shadow-black/20">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-on-surface text-xl font-bold">New comparison</h2>
            <p className="text-on-surface-variant text-sm">One YouTube URL and one Instagram Reel URL are required.</p>
          </div>
          <Radio className="text-tertiary h-5 w-5" aria-hidden="true" />
        </div>

        <form className="space-y-5">
          <label className="block">
            <span className="text-on-surface-variant text-sm font-medium">YouTube Video URL</span>
            <div className="border-outline-variant bg-surface-container-lowest mt-2 flex items-center gap-3 rounded-lg border px-3 py-3">
              <Film className="text-primary h-5 w-5 shrink-0" aria-hidden="true" />
              <input
                className="text-on-surface placeholder:text-outline w-full bg-transparent text-sm outline-none"
                placeholder="https://www.youtube.com/watch?v=..."
                type="url"
              />
            </div>
          </label>

          <label className="block">
            <span className="text-on-surface-variant text-sm font-medium">Instagram Reel URL</span>
            <div className="border-outline-variant bg-surface-container-lowest mt-2 flex items-center gap-3 rounded-lg border px-3 py-3">
              <Sparkles className="text-secondary h-5 w-5 shrink-0" aria-hidden="true" />
              <input
                className="text-on-surface placeholder:text-outline w-full bg-transparent text-sm outline-none"
                placeholder="https://www.instagram.com/reel/..."
                type="url"
              />
            </div>
          </label>

          <button
            className="bg-primary text-on-primary flex h-12 w-full items-center justify-center gap-2 rounded-lg font-bold transition hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-primary/40"
            type="button"
          >
            <Activity className="h-5 w-5" aria-hidden="true" />
            Analyze
          </button>
        </form>
      </section>
    </main>
  )
}

function PlaceholderPage({ title }) {
  return (
    <main className="mx-auto min-h-[calc(100vh-64px)] max-w-5xl px-4 py-12 sm:px-6">
      <div className="border-outline-variant bg-surface-container rounded-2xl border p-8">
        <p className="text-primary mb-2 text-sm font-semibold uppercase tracking-[0.25em]">ClipIQ</p>
        <h1 className="text-on-surface text-3xl font-bold">{title}</h1>
        <p className="text-on-surface-variant mt-3">
          This route is ready for the next feature branch implementation.
        </p>
      </div>
    </main>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-background text-on-surface">
      <Header />
      <Routes>
        <Route path="/" element={<CreateComparisonPage />} />
        <Route path="/comparisons/:comparisonId" element={<PlaceholderPage title="Comparison detail" />} />
        <Route path="/history" element={<PlaceholderPage title="Recent comparisons" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
