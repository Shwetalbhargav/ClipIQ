import { AlertCircle, Clapperboard, Loader2, PlaySquare } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createComparison } from '../api/comparisons.js'
import StatusBadge from '../components/ui/StatusBadge.jsx'
import { ROUTES } from '../constants/app.js'
import { useLocalHistory } from '../hooks/useLocalHistory.js'
import { validateComparisonUrls } from '../utils/validators.js'

function CreateComparisonPage() {
  const navigate = useNavigate()
  const { addItem } = useLocalHistory()
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [instagramUrl, setInstagramUrl] = useState('')
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    const nextErrors = validateComparisonUrls({ youtubeUrl, instagramUrl })
    setErrors(nextErrors)
    setSubmitError(null)
    if (Object.keys(nextErrors).length > 0) return

    setIsSubmitting(true)
    try {
      const comparison = await createComparison({ youtubeUrl, instagramUrl })
      addItem(comparison)
      navigate(ROUTES.comparison(comparison.id))
    } catch (error) {
      setSubmitError(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Creator RAG Analytics</p>
          <h1 className="mt-2 text-3xl font-bold tracking-normal text-on-surface sm:text-4xl">Compare YouTube vs Instagram Reels</h1>
        </div>
        <StatusBadge tone="neutral" label="Exactly two videos" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-xl border border-outline-variant bg-surface-container">
          <div className="border-b border-outline-variant bg-surface-container-high px-4 py-3">
            <h2 className="text-base font-semibold text-on-surface">New comparison</h2>
          </div>

          <form className="space-y-5 p-4 sm:p-6" onSubmit={handleSubmit}>
            <label className="block" htmlFor="youtube-url">
              <span className="text-sm font-semibold text-on-surface">Video A · YouTube video URL</span>
              <span className="mt-2 flex items-center gap-3 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-3 focus-within:ring-2 focus-within:ring-primary/70">
                <PlaySquare className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                <input
                  id="youtube-url"
                  type="url"
                  value={youtubeUrl}
                  onChange={(event) => setYoutubeUrl(event.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none placeholder:text-outline"
                  aria-describedby={errors.youtubeUrl ? 'youtube-url-error' : undefined}
                  aria-invalid={Boolean(errors.youtubeUrl)}
                />
              </span>
              {errors.youtubeUrl && <span id="youtube-url-error" className="mt-2 block text-sm text-error">{errors.youtubeUrl}</span>}
            </label>

            <label className="block" htmlFor="instagram-url">
              <span className="text-sm font-semibold text-on-surface">Video B · Instagram Reel URL</span>
              <span className="mt-2 flex items-center gap-3 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-3 focus-within:ring-2 focus-within:ring-secondary/70">
                <Clapperboard className="h-5 w-5 shrink-0 text-secondary" aria-hidden="true" />
                <input
                  id="instagram-url"
                  type="url"
                  value={instagramUrl}
                  onChange={(event) => setInstagramUrl(event.target.value)}
                  placeholder="https://www.instagram.com/reel/..."
                  className="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none placeholder:text-outline"
                  aria-describedby={errors.instagramUrl ? 'instagram-url-error' : undefined}
                  aria-invalid={Boolean(errors.instagramUrl)}
                />
              </span>
              {errors.instagramUrl && <span id="instagram-url-error" className="mt-2 block text-sm text-error">{errors.instagramUrl}</span>}
            </label>

            {submitError && (
              <div className="flex gap-2 rounded-lg border border-error/40 bg-error/10 p-3 text-sm text-error" role="alert">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{submitError}</span>
              </div>
            )}

            <button
              type="submit"
              className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-on-primary outline-none transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-primary/70"
              disabled={isSubmitting}
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isSubmitting ? 'Creating comparison' : 'Analyze videos'}
            </button>
          </form>
        </section>

        <aside className="rounded-xl border border-outline-variant bg-surface-container p-4">
          <h2 className="text-base font-semibold text-on-surface">Processing states</h2>
          <div className="mt-4 space-y-3">
            <StatusBadge tone="ready" label="Ready" />
            <StatusBadge tone="partial" label="Partial" />
            <StatusBadge tone="failed" label="Failed" />
          </div>
          <p className="mt-4 text-sm leading-6 text-on-surface-variant">
            Missing metrics, transcripts, thumbnails, citations, and backend fields are displayed as unavailable.
          </p>
        </aside>
      </div>
    </div>
  )
}

export default CreateComparisonPage
