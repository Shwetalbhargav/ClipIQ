import { Bot, Send, User } from 'lucide-react'
import { useState } from 'react'
import { normalizeCitation, sendFallbackChat, streamChat } from '../../api/chat.js'
import { formatTimestampRange } from '../../utils/formatters.js'

function ChatPanel({ comparisonId, disabled }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    const message = input.trim()
    if (!message || isStreaming) return

    const userMessage = { id: crypto.randomUUID(), role: 'user', content: message, citations: [], status: 'complete' }
    const assistantId = crypto.randomUUID()
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: 'assistant', content: '', citations: [], status: 'streaming' },
    ])
    setInput('')
    setError(null)
    setIsStreaming(true)

    try {
      await streamChat({
        comparisonId,
        message,
        onEvent: (eventPayload) => {
          if (eventPayload.type === 'delta') {
            setMessages((current) =>
              current.map((item) => (item.id === assistantId ? { ...item, content: item.content + (eventPayload.text || '') } : item)),
            )
          }

          if (eventPayload.type === 'citation') {
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId ? { ...item, citations: [...item.citations, normalizeCitation(eventPayload)] } : item,
              ),
            )
          }

          if (eventPayload.type === 'error') {
            throw new Error(eventPayload.error?.message || 'The stream failed.')
          }
        },
      })
      setMessages((current) => current.map((item) => (item.id === assistantId ? { ...item, status: 'complete' } : item)))
    } catch {
      try {
        const fallback = await sendFallbackChat({ comparisonId, message })
        setMessages((current) => current.map((item) => (item.id === assistantId ? fallback : item)))
      } catch (fallbackError) {
        setError(fallbackError.message)
        setMessages((current) =>
          current.map((item) => (item.id === assistantId ? { ...item, status: 'failed', content: 'Answer unavailable.' } : item)),
        )
      }
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <section className="flex min-h-[480px] flex-col rounded-xl border border-outline-variant bg-surface-container">
      <div className="border-b border-outline-variant bg-surface-container-high px-4 py-3">
        <h2 className="flex items-center gap-2 text-base font-semibold text-on-surface">
          <Bot className="h-4 w-4 text-primary" aria-hidden="true" />
          RAG chat
        </h2>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="rounded-lg border border-dashed border-outline-variant bg-surface-container-low p-4 text-sm text-on-surface-variant">
            Chat is available after the comparison is ready or partially usable.
          </div>
        ) : (
          messages.map((message) => (
            <article key={message.id} className="rounded-lg border border-outline-variant bg-surface-container-low p-3">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase text-on-surface-variant">
                {message.role === 'user' ? <User className="h-3.5 w-3.5" aria-hidden="true" /> : <Bot className="h-3.5 w-3.5" aria-hidden="true" />}
                {message.role}
              </div>
              <p className="whitespace-pre-wrap text-sm leading-6 text-on-surface">{message.content || 'Waiting for response...'}</p>
              {message.citations.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.citations.map((citation) => (
                    <div key={citation.id} className="rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-xs">
                      <p className="font-semibold text-on-surface">
                        {citation.label} · {formatTimestampRange(citation.startSeconds, citation.endSeconds)}
                      </p>
                      <p className="mt-1 line-clamp-3 text-on-surface-variant">{citation.text || 'Citation excerpt unavailable.'}</p>
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))
        )}
      </div>

      {error && <p className="border-t border-outline-variant px-4 py-2 text-sm text-error">{error}</p>}

      <form className="flex gap-2 border-t border-outline-variant p-3" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="chat-message">
          Ask about this comparison
        </label>
        <input
          id="chat-message"
          className="min-w-0 flex-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none placeholder:text-outline focus:ring-2 focus:ring-primary/70"
          placeholder="Ask why one video performed better"
          value={input}
          disabled={disabled || isStreaming}
          onChange={(event) => setInput(event.target.value)}
        />
        <button
          type="submit"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-on-primary outline-none transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary/70"
          disabled={disabled || isStreaming || !input.trim()}
          aria-label="Send chat message"
        >
          <Send className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>
    </section>
  )
}

export default ChatPanel
