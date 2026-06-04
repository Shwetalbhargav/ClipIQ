import { apiUrl, requestJson } from './client.js'

export function normalizeCitation(citation) {
  return {
    id: citation?.citation_id || `${citation?.video_id || 'source'}-${citation?.chunk_index ?? 'unknown'}`,
    label: citation?.label || 'Citation',
    videoId: citation?.video_id || null,
    chunkIndex: citation?.chunk_index ?? null,
    platform: citation?.platform || null,
    startSeconds: citation?.start_seconds ?? null,
    endSeconds: citation?.end_seconds ?? null,
    text: citation?.text || null,
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

export async function streamChat({ comparisonId, message, onEvent, signal }) {
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
      const dataLine = rawEvent
        .split('\n')
        .find((line) => line.startsWith('data:'))

      if (!dataLine) continue

      const rawData = dataLine.replace(/^data:\s?/, '')
      try {
        onEvent(JSON.parse(rawData))
      } catch {
        onEvent({ type: 'error', error: { message: 'Invalid stream event received.' } })
      }
    }
  }
}
