import { Bot, RefreshCw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { fallbackChat, streamChat } from '../../api/chat.js'
import Button from '../ui/Button.jsx'
import Card, { CardBody, CardHeader } from '../ui/Card.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import ErrorAlert from '../ui/ErrorAlert.jsx'
import ChatInput from './ChatInput.jsx'
import ChatMessage from './ChatMessage.jsx'

const SUGGESTED_QUESTIONS = [
  'Why did Video A get more engagement than Video B?',
  'What is the engagement rate of each?',
  'Compare the hooks in the first 5 seconds.',
  'Who is the creator of Video B?',
  'Suggest improvements for Video B based on Video A.',
]

function storageKey(comparisonId) {
  return `clipiq.chat.${comparisonId}`
}

function loadStoredMessages(comparisonId) {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey(comparisonId)) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function ChatPanel({ comparisonId, disabled }) {
  const [messages, setMessages] = useState(() => loadStoredMessages(comparisonId))
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [failedPrompt, setFailedPrompt] = useState(null)
  const canSend = !disabled && !isStreaming

  useEffect(() => {
    try {
      localStorage.setItem(storageKey(comparisonId), JSON.stringify(messages))
    } catch {
      // Local storage is a convenience fallback; chat still works in memory if it is unavailable.
    }
  }, [comparisonId, messages])

  const hasMessages = messages.length > 0
  const emptyStateBody = useMemo(() => {
    if (disabled) return 'Chat is available after the comparison is ready or partially usable.'
    return 'Ask about performance, transcript evidence, engagement, or differences between the two videos.'
  }, [disabled])

  async function sendMessage(message, { appendUser = true, useFallback = false } = {}) {
    if (!message || !canSend) return
    const userMessage = { id: crypto.randomUUID(), role: 'user', content: message, citations: [], status: 'complete' }
    const assistantId = crypto.randomUUID()
    setMessages((current) => [
      ...current,
      ...(appendUser ? [userMessage] : []),
      { id: assistantId, role: 'assistant', content: '', citations: [], status: useFallback ? 'sending' : 'streaming' },
    ])
    setInput('')
    setError(null)
    setFailedPrompt(null)
    setIsStreaming(true)

    try {
      if (useFallback) {
        const fallback = await fallbackChat(comparisonId, message)
        setMessages((current) => current.map((item) => (item.id === assistantId ? fallback : item)))
      } else {
        let streamFailed = null
        await streamChat(comparisonId, message, {
          onDelta: (text) => {
            setMessages((current) =>
              current.map((item) => (item.id === assistantId ? { ...item, content: item.content + text } : item)),
            )
          },
          onCitation: (citation) => {
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId ? { ...item, citations: [...(item.citations || []), citation] } : item,
              ),
            )
          },
          onError: (streamError) => {
            streamFailed = streamError
          },
        })

        if (streamFailed) {
          throw new Error(streamFailed.message || 'The response stream failed before completion.')
        }

        setMessages((current) => current.map((item) => (item.id === assistantId ? { ...item, status: 'complete' } : item)))
      }
    } catch (chatError) {
      setError(chatError.message || 'Chat is unavailable right now.')
      setFailedPrompt(message)
      setMessages((current) => current.map((item) => (item.id === assistantId ? { ...item, status: 'failed' } : item)))
    } finally {
      setIsStreaming(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    const message = input.trim()
    if (!message) return
    sendMessage(message)
  }

  return (
    <Card className="flex min-h-[480px] flex-col overflow-hidden">
      <CardHeader>
        <h2 className="flex items-center gap-2 text-base font-semibold text-on-surface">
          <Bot className="h-4 w-4 text-primary" aria-hidden="true" />
          RAG chat
        </h2>
      </CardHeader>

      <CardBody className="flex-1 space-y-3 overflow-y-auto">
        {!hasMessages ? (
          <EmptyState title={disabled ? 'Chat unavailable until analysis is usable' : 'Ask about this comparison'} className="p-4" icon={Bot}>
            {emptyStateBody}
          </EmptyState>
        ) : (
          messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}

        {!disabled && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((question) => (
              <button
                key={question}
                type="button"
                className="rounded-full border border-outline-variant px-3 py-1.5 text-left text-xs font-semibold text-on-surface-variant outline-none transition hover:border-primary hover:text-on-surface focus-visible:ring-2 focus-visible:ring-primary/70 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!canSend}
                onClick={() => sendMessage(question)}
              >
                {question}
              </button>
            ))}
          </div>
        )}
      </CardBody>

      {error && (
        <ErrorAlert className="mx-3 mb-3" title="Chat response interrupted">
          <p>{error}</p>
          {failedPrompt && (
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" icon={RefreshCw} disabled={!canSend} onClick={() => sendMessage(failedPrompt, { appendUser: false })}>
                Retry stream
              </Button>
              <Button size="sm" variant="ghost" disabled={!canSend} onClick={() => sendMessage(failedPrompt, { appendUser: false, useFallback: true })}>
                Try standard response
              </Button>
            </div>
          )}
        </ErrorAlert>
      )}

      <ChatInput
        disabled={disabled || isStreaming}
        isStreaming={isStreaming}
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onSubmit={handleSubmit}
      />
    </Card>
  )
}

export default ChatPanel
