import { History } from 'lucide-react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/ui/EmptyState.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'
import { ROUTES } from '../constants/app.js'
import { useLocalHistory } from '../hooks/useLocalHistory.js'
import { formatDate, formatUnavailable } from '../utils/formatters.js'

function HistoryPage() {
  const { items } = useLocalHistory()

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Recent sessions</p>
        <h1 className="mt-2 text-3xl font-bold text-on-surface">Comparison history</h1>
      </div>

      {items.length === 0 ? (
        <EmptyState icon={History} title="No recent comparisons">
          History is stored locally after successful comparison creation.
        </EmptyState>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Link
              key={item.id}
              to={ROUTES.comparison(item.id)}
              className="block rounded-xl border border-outline-variant bg-surface-container p-4 outline-none transition hover:bg-surface-container-high focus-visible:ring-2 focus-visible:ring-primary/70"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-on-surface">{item.id}</p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    YouTube: {formatUnavailable(item.youtubeCreator)} - Instagram: {formatUnavailable(item.instagramCreator)}
                  </p>
                  <p className="mt-1 text-xs text-on-surface-variant">{formatDate(item.createdAt)}</p>
                </div>
                <StatusBadge tone={item.status} label={item.status || 'unknown'} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default HistoryPage
