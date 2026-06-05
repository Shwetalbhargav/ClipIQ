import { formatTimestampRange } from '../../utils/formatters.js'
import UnavailableValue from '../ui/UnavailableValue.jsx'

function CitationCard({ citation }) {
  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-xs">
      <p className="font-semibold text-on-surface">
        <UnavailableValue value={citation.label} /> - {formatTimestampRange(citation.startSeconds, citation.endSeconds)}
      </p>
      <UnavailableValue as="p" value={citation.text || 'Citation excerpt unavailable.'} className="mt-1 line-clamp-3 text-on-surface-variant" />
    </div>
  )
}

export default CitationCard
