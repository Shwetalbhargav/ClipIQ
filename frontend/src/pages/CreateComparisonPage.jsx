import { Clapperboard, PlaySquare } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createComparison } from '../api/comparisons.js'
import UrlInput from '../components/forms/UrlInput.jsx'
import Button from '../components/ui/Button.jsx'
import Card, { CardBody, CardHeader } from '../components/ui/Card.jsx'
import ErrorAlert from '../components/ui/ErrorAlert.jsx'
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
        <Card>
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
                {isSubmitting ? 'Creating comparison' : 'Analyze videos'}
              </Button>
            </form>
          </CardBody>
        </Card>

        <Card as="aside" className="p-4">
          <h2 className="text-base font-semibold text-on-surface">Processing states</h2>
          <div className="mt-4 space-y-3">
            <StatusBadge tone="ready" label="Ready" />
            <StatusBadge tone="partial" label="Partial" />
            <StatusBadge tone="failed" label="Failed" />
          </div>
          <p className="mt-4 text-sm leading-6 text-on-surface-variant">
            Missing metrics, transcripts, thumbnails, citations, and backend fields are displayed as unavailable.
          </p>
        </Card>
      </div>
    </div>
  )
}

export default CreateComparisonPage
