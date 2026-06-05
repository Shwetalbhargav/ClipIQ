import { formatTimestampRange } from '../../utils/formatters.js'
import UnavailableValue from '../ui/UnavailableValue.jsx'

function sourceLabel(citation) {
  if (citation.videoId === 'A') return 'Video A'
  if (citation.videoId === 'B') return 'Video B'
  return null
}

function formatScore(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return null
  return score.toFixed(3)
}

function CitationCard({ citation }) {
  const score = formatScore(citation.score)
  const label = sourceLabel(citation)
  const timestamp =
    typeof citation.startSeconds === 'number' && typeof citation.endSeconds === 'number'
      ? formatTimestampRange(citation.startSeconds, citation.endSeconds)
      : null

  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        {label ? (
          <span className="rounded-md bg-primary px-2 py-1 font-semibold text-on-primary">{label}</span>
        ) : (
          <UnavailableValue value={label} />
        )}
        <span className="font-semibold text-on-surface">
          Chunk <UnavailableValue value={citation.chunkIndex} />
        </span>
        <UnavailableValue value={timestamp} className="text-on-surface-variant" />
        <UnavailableValue value={citation.platform} className="capitalize text-on-surface-variant" />
        {score && <span className="text-on-surface-variant">score {score}</span>}
      </div>
      {citation.label && (
        <p className="mt-2 font-medium text-on-surface">
          <UnavailableValue value={citation.label} />
        </p>
      )}
      <div className="mt-1 line-clamp-3 text-on-surface-variant">
        <UnavailableValue value={citation.text} />
      </div>
    </div>
  )
}

export default CitationCard
