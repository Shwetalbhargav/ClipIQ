import { BarChart3, BookOpen, Clapperboard, FileText, MessageSquare, PlaySquare, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createComparison } from '../api/comparisons.js'
import UrlInput from '../components/forms/UrlInput.jsx'
import Button from '../components/ui/Button.jsx'
import Card, { CardBody, CardHeader } from '../components/ui/Card.jsx'
import ErrorAlert from '../components/ui/ErrorAlert.jsx'
import HealthBadge from '../components/ui/HealthBadge.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'
import { ROUTES } from '../constants/app.js'
import { useHealth } from '../hooks/useHealth.js'
import { useLocalHistory } from '../hooks/useLocalHistory.js'
import { validateComparisonUrls } from '../utils/validators.js'

const featureTiles = [
  {
    title: 'Transcript RAG',
    description: 'Searchable transcript chunks power source-cited answers when extraction succeeds.',
    icon: FileText,
  },
  {
    title: 'Engagement Metrics',
    description: 'Backend metrics render only when returned by the comparison payload.',
    icon: BarChart3,
  },
  {
    title: 'Streaming Chat',
    description: 'Ask follow-up questions against the completed comparison session.',
    icon: MessageSquare,
  },
  {
    title: 'Source Citations',
    description: 'Answers can reference transcript chunks instead of unsupported claims.',
    icon: BookOpen,
  },
]

function CreateComparisonPage() {
  const navigate = useNavigate()
  const health = useHealth()
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
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-3xl">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Creator RAG Analytics</p>
            <HealthBadge compact status={health.status} />
          </div>
          <h1 className="text-3xl font-bold tracking-normal text-on-surface sm:text-5xl">
            Compare YouTube vs Instagram Reels with source-cited AI
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-on-surface-variant sm:text-lg">
            Submit exactly one YouTube video and exactly one Instagram Reel to create a comparison session.
          </p>
        </div>
        <StatusBadge className="w-fit" tone="neutral" label="Exactly two videos" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,640px)_minmax(320px,1fr)]">
        <div className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader>
              <h2 className="text-base font-semibold text-on-surface">New comparison</h2>
            </CardHeader>

            <CardBody className="sm:p-6">
              <form className="space-y-5" onSubmit={handleSubmit}>
                <UrlInput
                  id="youtube-url"
                  label="Video A - YouTube video URL"
                  required
                  icon={PlaySquare}
                  value={youtubeUrl}
                  onChange={(event) => setYoutubeUrl(event.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  error={errors.youtubeUrl}
                />

                <UrlInput
                  id="instagram-url"
                  label="Video B - Instagram Reel URL"
                  required
                  icon={Clapperboard}
                  tone="secondary"
                  value={instagramUrl}
                  onChange={(event) => setInstagramUrl(event.target.value)}
                  placeholder="https://www.instagram.com/reel/..."
                  error={errors.instagramUrl}
                />

                {submitError && <ErrorAlert>{submitError}</ErrorAlert>}

                <Button type="submit" variant="primary" size="lg" className="w-full" isLoading={isSubmitting}>
                  {isSubmitting ? 'Creating comparison' : 'Analyze'}
                </Button>
                <p className="flex gap-2 text-xs leading-5 text-on-surface-variant">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  Backend health is informational only. You can type and submit while it is checking or offline.
                </p>
              </form>
            </CardBody>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            {featureTiles.map(({ title, description, icon: Icon }) => (
              <Card key={title} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm font-semibold text-on-surface">{title}</h3>
                  <Icon className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                </div>
                <p className="mt-4 text-sm leading-6 text-on-surface-variant">{description}</p>
              </Card>
            ))}
          </div>
        </div>

        <Card as="aside" className="p-5">
          <h2 className="text-base font-semibold text-on-surface">Processing states</h2>
          <div className="mt-5 flex flex-wrap gap-2">
            <StatusBadge tone="ready" label="Ready" />
            <StatusBadge tone="partial" label="Partial" />
            <StatusBadge tone="failed" label="Failed" />
          </div>
          <div className="mt-6 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
            <p className="text-sm font-semibold text-on-surface">Unavailable values stay visible</p>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Missing metrics, transcripts, thumbnails, citations, and backend fields are displayed as unavailable instead of being guessed.
            </p>
          </div>
          <div className="mt-4 rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
            <p className="text-sm font-semibold text-on-surface">Supported sources</p>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Video A must be a YouTube watch URL. Video B must be an Instagram Reel URL.
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default CreateComparisonPage
