import { RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getComparison } from '../api/comparisons.js'
import ChatPanel from '../components/chat/ChatPanel.jsx'
import EngagementSummary from '../components/comparison/EngagementSummary.jsx'
import VideoCard from '../components/comparison/VideoCard.jsx'
import Button from '../components/ui/Button.jsx'
import Card from '../components/ui/Card.jsx'
import ErrorAlert from '../components/ui/ErrorAlert.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'
import { compareEngagement } from '../utils/engagement.js'
import { formatDate } from '../utils/formatters.js'

function statusTone(status) {
  if (status === 'ready') return 'ready'
  if (status === 'partial') return 'partial'
  if (status === 'failed') return 'failed'
  return 'neutral'
}

function ComparisonPage() {
  const { comparisonId } = useParams()
  const [state, setState] = useState({ status: 'loading', comparison: null, error: null })

  const loadComparison = useCallback(async ({ showLoading = true } = {}) => {
    if (showLoading) {
      setState((current) => ({ ...current, status: 'loading', error: null }))
    }
    try {
      const comparison = await getComparison(comparisonId)
      setState({ status: 'loaded', comparison, error: null })
    } catch (error) {
      setState({ status: error.status === 404 ? 'not-found' : 'error', comparison: null, error })
    }
  }, [comparisonId])

  useEffect(() => {
    let active = true

    getComparison(comparisonId)
      .then((comparison) => {
        if (active) setState({ status: 'loaded', comparison, error: null })
      })
      .catch((error) => {
        if (active) setState({ status: error.status === 404 ? 'not-found' : 'error', comparison: null, error })
      })

    return () => {
      active = false
    }
  }, [comparisonId])

  if (state.status === 'loading') {
    return (
      <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4">
        <Card className="w-full max-w-sm p-6 text-center">
          <Skeleton className="mx-auto h-8 w-8 rounded-full" />
          <p className="mt-3 text-sm font-semibold text-on-surface">Loading comparison</p>
          <Skeleton className="mt-4 h-3 w-full" />
        </Card>
      </div>
    )
  }

  if (state.status === 'not-found' || state.status === 'error') {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <Card className="p-6">
          <ErrorAlert title={state.status === 'not-found' ? 'Comparison not found' : 'Unable to load comparison'}>
            {state.error?.message || 'The backend did not return a usable comparison.'}
          </ErrorAlert>
          <Button
            className="mt-5"
            icon={RefreshCw}
            onClick={() => loadComparison()}
            type="button"
            variant="secondary"
          >
            Retry
          </Button>
        </Card>
      </div>
    )
  }

  const { comparison } = state
  const chatDisabled = comparison.status === 'failed'
  const engagement = compareEngagement(comparison.videoA, comparison.videoB)
  const winnerLabel = engagement.winner === 'A' || engagement.winner === 'B' ? engagement.winner : null

  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Comparison report</p>
          <h1 className="mt-2 truncate text-2xl font-bold text-on-surface sm:text-3xl">{comparison.id}</h1>
          <p className="mt-1 text-sm text-on-surface-variant">Updated {formatDate(comparison.updatedAt)}</p>
        </div>
        <StatusBadge tone={statusTone(comparison.status)} label={comparison.status} />
      </div>

      {comparison.errors.length > 0 && (
        <ErrorAlert className="mb-6" title="Comparison processing issues">
          <ul className="space-y-1">
            {comparison.errors.map((error, index) => (
              <li key={`${error.code || 'error'}-${index}`}>{error.message || error.code || 'Processing issue unavailable.'}</li>
            ))}
          </ul>
        </ErrorAlert>
      )}

      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="min-w-0 space-y-6">
          <EngagementSummary comparison={comparison} />
          <div className="grid min-w-0 gap-6 md:grid-cols-2">
            <VideoCard
              video={comparison.videoA}
              fallbackLabel="Video A"
              fallbackPlatform="YouTube"
              transcriptStatus={comparison.transcriptStatus}
              indexingStatus={comparison.indexingStatus}
              isWinner={winnerLabel === 'A'}
            />
            <VideoCard
              video={comparison.videoB}
              fallbackLabel="Video B"
              fallbackPlatform="Instagram Reel"
              transcriptStatus={comparison.transcriptStatus}
              indexingStatus={comparison.indexingStatus}
              isWinner={winnerLabel === 'B'}
            />
          </div>
        </div>
        <ChatPanel comparisonId={comparison.id} disabled={chatDisabled} />
      </div>
    </div>
  )
}

export default ComparisonPage
