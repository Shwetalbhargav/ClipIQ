import { Bot } from 'lucide-react'
import { useState } from 'react'
import { normalizeCitation, sendFallbackChat, streamChat } from '../../api/chat.js'
import Card, { CardBody, CardHeader } from '../ui/Card.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import ErrorAlert from '../ui/ErrorAlert.jsx'
import ChatInput from './ChatInput.jsx'
import ChatMessage from './ChatMessage.jsx'

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
    <Card className="flex min-h-[480px] flex-col">
      <CardHeader>
        <h2 className="flex items-center gap-2 text-base font-semibold text-on-surface">
          <Bot className="h-4 w-4 text-primary" aria-hidden="true" />
          RAG chat
        </h2>
      </CardHeader>

      <CardBody className="flex-1 space-y-3 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyState title={disabled ? 'Chat unavailable until analysis is usable' : 'Ask about this comparison'} className="p-4" icon={Bot}>
            {disabled
              ? 'Chat is available after the comparison is ready or partially usable.'
              : 'Ask about performance, transcript evidence, engagement, or differences between the two videos.'}
          </EmptyState>
        ) : (
          messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}
      </CardBody>

      {error && <ErrorAlert className="mx-3 mb-3">{error}</ErrorAlert>}

      <ChatInput
        disabled={disabled}
        isStreaming={isStreaming}
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onSubmit={handleSubmit}
      />
    </Card>
  )
}

export default ChatPanel
