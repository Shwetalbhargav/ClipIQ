import { AlertCircle, CheckCircle2, Circle, Clock, ExternalLink, FileSearch, Loader2, PlaySquare, XCircle } from 'lucide-react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useMemo } from 'react'
import Button from '../components/ui/Button.jsx'
import Card, { CardBody, CardHeader } from '../components/ui/Card.jsx'
import ErrorAlert from '../components/ui/ErrorAlert.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'
import UnavailableValue from '../components/ui/UnavailableValue.jsx'
import { COMPARISON_STATUSES, ROUTES } from '../constants/app.js'
import { isTerminalComparisonStatus, useComparisonPolling } from '../hooks/useComparisonPolling.js'
import { formatDate } from '../utils/formatters.js'

function readStoredUrls(comparisonId) {
  try {
    return JSON.parse(sessionStorage.getItem(`clipiq.analysis.${comparisonId}`)) || null
  } catch {
    return null
  }
}

function statusTone(status) {
  if (status === COMPARISON_STATUSES.ready) return 'ready'
  if (status === COMPARISON_STATUSES.partial) return 'partial'
  if (status === COMPARISON_STATUSES.failed) return 'failed'
  return 'neutral'
}

function checklistTone(status) {
  if (status === 'complete') return 'text-tertiary'
  if (status === 'failed') return 'text-error'
  if (status === 'active') return 'text-primary'
  return 'text-outline'
}

function ChecklistStatusIcon({ status }) {
  const className = `h-5 w-5 shrink-0 ${checklistTone(status)} ${status === 'active' ? 'animate-spin' : ''}`

  if (status === 'complete') return <CheckCircle2 className={className} aria-hidden="true" />
  if (status === 'failed') return <XCircle className={className} aria-hidden="true" />
  if (status === 'active') return <Loader2 className={className} aria-hidden="true" />
  return <Circle className={className} aria-hidden="true" />
}

function buildChecklist(comparison) {
  const isTerminal = isTerminalComparisonStatus(comparison?.status)
  const isFailed = comparison?.status === COMPARISON_STATUSES.failed
  const hasTranscriptStatus = Object.keys(comparison?.transcriptStatus || {}).length > 0

  return [
    {
      label: 'Validating URLs',
      status: comparison ? 'complete' : 'active',
    },
    {
      label: 'Creating comparison session',
      status: comparison?.id ? 'complete' : 'active',
    },
    {
      label: 'Receiving YouTube metadata',
      status: comparison?.videoA ? 'complete' : isTerminal ? 'failed' : comparison ? 'active' : 'pending',
    },
    {
      label: 'Receiving Instagram Reel metadata',
      status: comparison?.videoB ? 'complete' : isTerminal ? 'failed' : comparison ? 'active' : 'pending',
    },
    {
      label: 'Receiving transcript/index status',
      status: hasTranscriptStatus ? 'complete' : isFailed ? 'failed' : comparison ? 'active' : 'pending',
    },
    {
      label: 'Preparing comparison result',
      status: isFailed ? 'failed' : isTerminal ? 'complete' : comparison ? 'active' : 'pending',
    },
  ]
}

function VideoPreview({ label, platform, url, video }) {
  return (
    <Card className="min-w-0 p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-outline-variant bg-surface-container-lowest">
          <PlaySquare className="h-5 w-5 text-primary" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{platform}</p>
          <h2 className="mt-1 text-sm font-semibold text-on-surface">{label}</h2>
          <UnavailableValue as="p" value={video?.title || video?.caption} className="mt-1 truncate text-sm text-on-surface" />
          <UnavailableValue as="p" value={video?.canonicalUrl || video?.sourceUrl || url} className="mt-1 break-all text-xs text-on-surface-variant" />
        </div>
      </div>
    </Card>
  )
}

function ChecklistItem({ item }) {
  return (
    <li className="flex min-w-0 items-center gap-3">
      <ChecklistStatusIcon status={item.status} />
      <span className={`min-w-0 flex-1 ${item.status === 'pending' ? 'text-on-surface-variant' : 'text-on-surface'}`}>{item.label}</span>
      <span className="shrink-0 text-xs font-semibold uppercase text-on-surface-variant">{item.status}</span>
    </li>
  )
}

function AnalysisLoadingPage() {
  const { comparisonId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const storedUrls = useMemo(() => readStoredUrls(comparisonId), [comparisonId])
  const submittedUrls = location.state?.submittedUrls || storedUrls || {}
  const initialComparison = location.state?.initialComparison || null
  const { comparison, error, isPolling } = useComparisonPolling(comparisonId, { initialComparison })
  const checklist = buildChecklist(comparison)
  const isTerminal = isTerminalComparisonStatus(comparison?.status)

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Analysis</p>
          <h1 className="mt-2 text-3xl font-bold text-on-surface">Analyzing videos</h1>
        </div>
        <Button type="button" variant="secondary" onClick={() => navigate(ROUTES.create)}>
          Cancel analysis
        </Button>
      </div>

      <Card className="overflow-hidden">
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-on-surface">Processing checklist</h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              Polling stops when the comparison returns ready, partial, or failed.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {comparison?.status && <StatusBadge tone={statusTone(comparison.status)} label={comparison.status} />}
            {isPolling && <StatusBadge tone="neutral" label="Polling" />}
          </div>
        </CardHeader>
        <CardBody className="space-y-5">
          {error && (
            <ErrorAlert title="Could not refresh comparison">
              {error.message || 'Polling failed. The latest known status is still shown if available.'}
            </ErrorAlert>
          )}

          <ul className="space-y-4" aria-label="Analysis progress checklist">
            {checklist.map((item) => (
              <ChecklistItem key={item.label} item={item} />
            ))}
          </ul>

          <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-4 text-sm text-on-surface-variant">
            <div className="flex gap-2">
              <Clock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>Some videos require extra extraction time. ClipIQ shows only backend-returned status, not estimated percent complete or timing.</p>
            </div>
          </div>
        </CardBody>
      </Card>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <VideoPreview label="Video A" platform="YouTube" url={submittedUrls.youtubeUrl} video={comparison?.videoA} />
        <VideoPreview label="Video B" platform="Instagram Reel" url={submittedUrls.instagramUrl} video={comparison?.videoB} />
      </div>

      {isTerminal && (
        <Card className="mt-6 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-sm font-semibold text-on-surface">
                {comparison.status === COMPARISON_STATUSES.failed ? (
                  <AlertCircle className="h-4 w-4 text-error" aria-hidden="true" />
                ) : (
                  <FileSearch className="h-4 w-4 text-tertiary" aria-hidden="true" />
                )}
                Comparison status: {comparison.status}
              </p>
              <p className="mt-1 text-sm text-on-surface-variant">Updated {formatDate(comparison.updatedAt)}</p>
            </div>
            <Button type="button" variant="primary" icon={ExternalLink} onClick={() => navigate(ROUTES.comparison(comparison.id))}>
              Open comparison
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}

export default AnalysisLoadingPage
