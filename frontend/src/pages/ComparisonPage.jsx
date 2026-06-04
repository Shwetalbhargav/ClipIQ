import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { isNotFoundError } from '../api/client.js'
import { getComparison } from '../api/comparisons.js'
import ChatPanel from '../components/chat/ChatPanel.jsx'
import VideoCard from '../components/comparison/VideoCard.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'
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
      setState({ status: isNotFoundError(error) ? 'not-found' : 'error', comparison: null, error })
    }
  }, [comparisonId])

  useEffect(() => {
    let active = true

    getComparison(comparisonId)
      .then((comparison) => {
        if (active) setState({ status: 'loaded', comparison, error: null })
      })
      .catch((error) => {
        if (active) setState({ status: isNotFoundError(error) ? 'not-found' : 'error', comparison: null, error })
      })

    return () => {
      active = false
    }
  }, [comparisonId])

  if (state.status === 'loading') {
    return (
      <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4">
        <div className="rounded-xl border border-outline-variant bg-surface-container p-6 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-on-surface">Loading comparison</p>
        </div>
      </div>
    )
  }

  if (state.status === 'not-found' || state.status === 'error') {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <div className="rounded-xl border border-outline-variant bg-surface-container p-6">
          <AlertCircle className="h-6 w-6 text-error" aria-hidden="true" />
          <h1 className="mt-3 text-2xl font-bold text-on-surface">{state.status === 'not-found' ? 'Comparison not found' : 'Unable to load comparison'}</h1>
          <p className="mt-2 text-sm text-on-surface-variant">{state.error?.message || 'The backend did not return a usable comparison.'}</p>
          <button
            type="button"
            onClick={loadComparison}
            className="mt-5 inline-flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-high px-3 py-2 text-sm font-semibold text-on-surface outline-none hover:bg-surface-container-highest focus-visible:ring-2 focus-visible:ring-primary/70"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  const { comparison } = state
  const chatDisabled = comparison.status === 'failed'

  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Comparison</p>
          <h1 className="mt-2 truncate text-2xl font-bold text-on-surface sm:text-3xl">{comparison.id}</h1>
          <p className="mt-1 text-sm text-on-surface-variant">Updated {formatDate(comparison.updatedAt)}</p>
        </div>
        <StatusBadge tone={statusTone(comparison.status)} label={comparison.status} />
      </div>

      {comparison.errors.length > 0 && (
        <div className="mb-6 rounded-xl border border-error/40 bg-error/10 p-4 text-sm text-error">
          <p className="font-semibold">Backend reported issues</p>
          <ul className="mt-2 space-y-1">
            {comparison.errors.map((error, index) => (
              <li key={`${error.code || 'error'}-${index}`}>{error.message || error.code || 'Processing issue unavailable.'}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="grid min-w-0 gap-6 md:grid-cols-2">
          <VideoCard video={comparison.videoA} />
          <VideoCard video={comparison.videoB} />
        </div>
        <ChatPanel comparisonId={comparison.id} disabled={chatDisabled} />
      </div>
    </div>
  )
}

export default ComparisonPage
