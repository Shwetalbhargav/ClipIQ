import { Bot, User } from 'lucide-react'
import CitationCard from './CitationCard.jsx'

function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const Icon = isUser ? User : Bot

  return (
    <article className="rounded-lg border border-outline-variant bg-surface-container-low p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase text-on-surface-variant">
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {message.role}
      </div>
      <p className="whitespace-pre-wrap text-sm leading-6 text-on-surface">{message.content || 'Waiting for response...'}</p>
      {message.citations.length > 0 && (
        <div className="mt-3 space-y-2">
          {message.citations.map((citation) => (
            <CitationCard key={citation.id} citation={citation} />
          ))}
        </div>
      )}
    </article>
  )
}

export default ChatMessage
