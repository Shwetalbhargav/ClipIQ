import { BarChart3, BookOpen, Clapperboard, FileText, MessageSquare, PlaySquare, Sparkles } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createComparison } from '../api/comparisons.js'
import UrlInput from '../components/forms/UrlInput.jsx'
import Button from '../components/ui/Button.jsx'
import Card, { CardBody, CardHeader } from '../components/ui/Card.jsx'
import ErrorAlert from '../components/ui/ErrorAlert.jsx'
import HealthBadge from '../components/ui/HealthBadge.jsx'
import ServiceDiagnostics from '../components/ui/ServiceDiagnostics.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'
import { ROUTES } from '../constants/app.js'
import { useHealth } from '../hooks/useHealth.js'
import { useLocalHistory } from '../hooks/useLocalHistory.js'
import { getFirstComparisonUrlErrorField, validateComparisonUrls } from '../utils/validators.js'

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

function submitHelperText(status) {
  if (status === 'online') {
    return 'Backend health is online. Platform extraction can still fail if a source requires login or rate-limits access.'
  }
  if (status === 'loading') {
    return 'Checking backend health. You can keep typing while the health check completes.'
  }
  if (status === 'degraded') {
    return 'Backend health is degraded. You can submit, but comparison creation may return partial or failed results.'
  }
  return 'Backend appears offline. You can still edit URLs, but submit may fail until the API is reachable.'
}

function CreateComparisonPage() {
  const navigate = useNavigate()
  const health = useHealth()
  const { addItem } = useLocalHistory()
  const youtubeInputRef = useRef(null)
  const instagramInputRef = useRef(null)
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [instagramUrl, setInstagramUrl] = useState('')
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [hasSubmitAttempt, setHasSubmitAttempt] = useState(false)
  const currentErrors = useMemo(() => validateComparisonUrls({ youtubeUrl, instagramUrl }), [youtubeUrl, instagramUrl])
  const visibleErrors = hasSubmitAttempt ? currentErrors : errors
  const isSubmitBlocked = hasSubmitAttempt && Object.keys(currentErrors).length > 0

  async function handleSubmit(event) {
    event.preventDefault()
    setHasSubmitAttempt(true)
    const nextErrors = validateComparisonUrls({ youtubeUrl, instagramUrl })
    setErrors(nextErrors)
    setSubmitError(null)
    if (Object.keys(nextErrors).length > 0) {
      const firstInvalidField = getFirstComparisonUrlErrorField(nextErrors)
      if (firstInvalidField === 'youtube-url') youtubeInputRef.current?.focus()
      if (firstInvalidField === 'instagram-url') instagramInputRef.current?.focus()
      return
    }

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
                  ref={youtubeInputRef}
                  label="Video A - YouTube video URL"
                  required
                  icon={PlaySquare}
                  value={youtubeUrl}
                  onChange={(event) => {
                    setYoutubeUrl(event.target.value)
                    setSubmitError(null)
                  }}
                  placeholder="https://www.youtube.com/watch?v=..."
                  error={visibleErrors.youtubeUrl}
                />

                <UrlInput
                  id="instagram-url"
                  ref={instagramInputRef}
                  label="Video B - Instagram Reel URL"
                  required
                  icon={Clapperboard}
                  tone="secondary"
                  value={instagramUrl}
                  onChange={(event) => {
                    setInstagramUrl(event.target.value)
                    setSubmitError(null)
                  }}
                  placeholder="https://www.instagram.com/reel/..."
                  error={visibleErrors.instagramUrl}
                />

                {submitError && <ErrorAlert>{submitError}</ErrorAlert>}

                {isSubmitBlocked && (
                  <ErrorAlert title="Fix validation errors">
                    Submit is disabled until Video A is a YouTube watch URL and Video B is an Instagram Reel URL.
                  </ErrorAlert>
                )}

                <Button type="submit" variant="primary" size="lg" className="w-full" isLoading={isSubmitting} disabled={isSubmitBlocked}>
                  {isSubmitting ? 'Creating comparison' : 'Analyze'}
                </Button>
                <p className={`flex gap-2 text-xs leading-5 ${health.status === 'online' || health.status === 'loading' ? 'text-on-surface-variant' : 'text-error'}`}>
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  {submitHelperText(health.status)}
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

        <div className="space-y-6">
          <ServiceDiagnostics health={health} />

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
    </div>
  )
}

export default CreateComparisonPage
