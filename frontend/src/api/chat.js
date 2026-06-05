import { apiUrl, requestJson } from './client.js'

export function normalizeCitation(citation) {
  return {
    id: citation?.citation_id || `${citation?.video_id || 'source'}-${citation?.chunk_index ?? 'unknown'}`,
    label: citation?.label || citation?.citation_id || null,
    videoId: citation?.video_id || null,
    chunkIndex: citation?.chunk_index ?? null,
    platform: citation?.platform || null,
    sourceUrl: citation?.source_url || null,
    startSeconds: citation?.start_seconds ?? null,
    endSeconds: citation?.end_seconds ?? null,
    text: citation?.text || null,
    score: typeof citation?.score === 'number' ? citation.score : null,
  }
}

export function normalizeChatResponse(payload) {
  return {
    id: payload?.response_id || crypto.randomUUID(),
    sessionId: payload?.session_id || null,
    role: 'assistant',
    content: payload?.answer || '',
    citations: Array.isArray(payload?.citations) ? payload.citations.map(normalizeCitation) : [],
    status: 'complete',
  }
}

export async function sendFallbackChat({ comparisonId, message }) {
  const payload = await requestJson('/chat', {
    method: 'POST',
    body: JSON.stringify({
      session_id: comparisonId,
      message,
      top_k: 8,
    }),
  })

  return normalizeChatResponse(payload)
}

export async function fallbackChat(comparisonId, message) {
  return sendFallbackChat({ comparisonId, message })
}

function parseSseEvent(rawEvent) {
  const lines = rawEvent.split('\n')
  const data = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.replace(/^data:\s?/, ''))
    .join('\n')

  if (!data || data === '[DONE]') return null

  try {
    return JSON.parse(data)
  } catch {
    return { type: 'error', error: { message: 'Invalid stream event received.' } }
  }
}

function dispatchStreamEvent(eventPayload, handlers) {
  if (!eventPayload) return

  handlers.onEvent?.(eventPayload)
  if (eventPayload.type === 'metadata') handlers.onMetadata?.(eventPayload)
  if (eventPayload.type === 'delta') handlers.onDelta?.(eventPayload.text || '')
  if (eventPayload.type === 'citation') handlers.onCitation?.(normalizeCitation(eventPayload))
  if (eventPayload.type === 'done') handlers.onDone?.(eventPayload)
  if (eventPayload.type === 'error') handlers.onError?.(eventPayload.error || { message: 'The stream failed.' })
}

export async function streamChat(comparisonIdOrOptions, messageArg, handlersArg = {}) {
  const options =
    typeof comparisonIdOrOptions === 'object'
      ? comparisonIdOrOptions
      : { comparisonId: comparisonIdOrOptions, message: messageArg, ...handlersArg }
  const { comparisonId, message, signal, ...handlers } = options

  const response = await fetch(apiUrl(`/comparisons/${encodeURIComponent(comparisonId)}/chat/stream`), {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(response.status === 404 ? 'Comparison not found or not ready for chat.' : 'Streaming chat is unavailable.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const rawEvent of events) {
      dispatchStreamEvent(parseSseEvent(rawEvent), handlers)
    }
  }

  if (buffer.trim()) {
    dispatchStreamEvent(parseSseEvent(buffer), handlers)
  }
}
