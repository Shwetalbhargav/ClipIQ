import { Bot, User } from 'lucide-react'
import StatusBadge from '../ui/StatusBadge.jsx'
import UnavailableValue from '../ui/UnavailableValue.jsx'
import CitationCard from './CitationCard.jsx'

function RetrievalDebug({ citations }) {
  if (!import.meta.env.DEV || citations.length === 0) return null

  const counts = citations.reduce(
    (accumulator, citation) => {
      if (citation.videoId === 'A') accumulator.A += 1
      if (citation.videoId === 'B') accumulator.B += 1
      if (typeof citation.score === 'number') {
        accumulator.bestScore = Math.max(accumulator.bestScore ?? citation.score, citation.score)
      }
      return accumulator
    },
    { A: 0, B: 0, bestScore: null },
  )

  const bestScore = typeof counts.bestScore === 'number' ? counts.bestScore.toFixed(3) : 'unavailable'

  return (
    <div className="rounded-lg border border-dashed border-outline-variant bg-surface-container-lowest px-3 py-2 text-xs text-on-surface-variant">
      Retrieval debug: Video A {counts.A} chunks, Video B {counts.B} chunks, best score {bestScore}
    </div>
  )
}

function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const Icon = isUser ? User : Bot
  const statusTone = message.status === 'failed' ? 'failed' : message.status === 'streaming' ? 'partial' : 'neutral'
  const citations = Array.isArray(message.citations) ? message.citations : []

  return (
    <article className="rounded-lg border border-outline-variant bg-surface-container-low p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase text-on-surface-variant">
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          {message.role}
        </div>
        {!isUser && message.status !== 'complete' && <StatusBadge compact tone={statusTone} label={message.status} />}
      </div>
      <div className="whitespace-pre-wrap text-sm leading-6 text-on-surface">
        <UnavailableValue value={message.content || null} />
      </div>
      {citations.length > 0 && (
        <div className="mt-3 space-y-2">
          <RetrievalDebug citations={citations} />
          {citations.map((citation) => (
            <CitationCard key={citation.id} citation={citation} />
          ))}
        </div>
      )}
    </article>
  )
}

export default ChatMessage
