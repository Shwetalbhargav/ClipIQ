import { API_ERROR_TYPES, ApiError, apiUrl, invalidPayloadError, requestJson } from './client.js'

function fallbackId(prefix = 'id') {
  return typeof globalThis.crypto?.randomUUID === 'function' ? globalThis.crypto.randomUUID() : `${prefix}-${Date.now()}`
}

function nullableString(value) {
  return typeof value === 'string' && value.trim() ? value : null
}

function nullableNumber(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function normalizeCitation(citation) {
  if (!citation || typeof citation !== 'object') {
    return {
      id: fallbackId('citation'),
      label: 'Citation',
      videoId: null,
      chunkIndex: null,
      platform: null,
      startSeconds: null,
      endSeconds: null,
      text: null,
    }
  }

  return {
    id: nullableString(citation.citation_id) || `${nullableString(citation.video_id) || 'source'}-${citation.chunk_index ?? 'unknown'}`,
    label: nullableString(citation.label) || 'Citation',
    videoId: nullableString(citation.video_id),
    chunkIndex: nullableNumber(citation.chunk_index),
    platform: nullableString(citation.platform),
    startSeconds: nullableNumber(citation.start_seconds),
    endSeconds: nullableNumber(citation.end_seconds),
    text: nullableString(citation.text),
  }
}

export function normalizeChatResponse(payload, { endpoint = null } = {}) {
  if (!payload || typeof payload !== 'object') {
    throw invalidPayloadError('The backend returned an invalid chat payload.', { endpoint, payload })
  }

  return {
    id: nullableString(payload.response_id) || fallbackId('response'),
    sessionId: nullableString(payload.session_id),
    role: 'assistant',
    content: nullableString(payload.answer) || '',
    citations: Array.isArray(payload.citations) ? payload.citations.map(normalizeCitation) : [],
    model: nullableString(payload.model),
    status: 'complete',
    usage: payload.usage && typeof payload.usage === 'object' && !Array.isArray(payload.usage) ? payload.usage : {},
  }
}

export async function sendFallbackChat({ comparisonId, message }) {
  const endpoint = '/chat'
  const payload = await requestJson(endpoint, {
    method: 'POST',
    body: JSON.stringify({
      session_id: comparisonId,
      message,
      top_k: 8,
    }),
  })

  return normalizeChatResponse(payload, { endpoint })
}

function normalizeStreamEvent(eventPayload) {
  if (!eventPayload || typeof eventPayload !== 'object') {
    return { type: 'error', error: { code: 'invalid_stream_event', message: 'Invalid stream event received.' } }
  }

  if (eventPayload.type === 'metadata') {
    return {
      type: 'metadata',
      comparisonId: nullableString(eventPayload.comparison_id),
      model: nullableString(eventPayload.model),
      responseId: nullableString(eventPayload.response_id),
      startedAt: nullableString(eventPayload.started_at),
    }
  }

  if (eventPayload.type === 'delta') {
    return { type: 'delta', text: nullableString(eventPayload.text) || '' }
  }

  if (eventPayload.type === 'citation') {
    return { type: 'citation', ...normalizeCitation(eventPayload) }
  }

  if (eventPayload.type === 'done') {
    return {
      type: 'done',
      responseId: nullableString(eventPayload.response_id),
      status: nullableString(eventPayload.status) || 'completed',
      usage: eventPayload.usage && typeof eventPayload.usage === 'object' && !Array.isArray(eventPayload.usage) ? eventPayload.usage : {},
    }
  }

  if (eventPayload.type === 'error') {
    return {
      type: 'error',
      error: {
        code: nullableString(eventPayload.error?.code) || 'stream_failed',
        message: nullableString(eventPayload.error?.message) || 'The response stream failed before completion. Please retry.',
      },
    }
  }

  return { type: 'error', error: { code: 'unknown_stream_event', message: 'Unknown stream event received.' } }
}

function parseSseMessage(rawEvent) {
  const data = rawEvent
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.replace(/^data:\s?/, ''))
    .join('\n')

  if (!data) return null

  try {
    return normalizeStreamEvent(JSON.parse(data))
  } catch {
    return { type: 'error', error: { code: 'invalid_stream_json', message: 'Invalid stream event received.' } }
  }
}

export async function streamChat({ comparisonId, message, onEvent, signal }) {
  const endpoint = `/comparisons/${encodeURIComponent(comparisonId)}/chat/stream`
  let response

  try {
    response = await fetch(apiUrl(endpoint), {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
      signal,
    })
  } catch (error) {
    throw new ApiError('Network error. Confirm the backend is running and reachable.', {
      details: error,
      endpoint,
      type: API_ERROR_TYPES.network,
    })
  }

  if (!response.ok || !response.body) {
    throw new ApiError(response.status === 404 ? 'Comparison not found or not ready for chat.' : 'Streaming chat is unavailable.', {
      endpoint,
      status: response.status,
      type: response.status === 404 ? API_ERROR_TYPES.notFound : API_ERROR_TYPES.serviceUnavailable,
    })
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
      const normalizedEvent = parseSseMessage(rawEvent)
      if (normalizedEvent) onEvent(normalizedEvent)
    }
  }

  if (buffer.trim()) {
    const normalizedEvent = parseSseMessage(buffer)
    if (normalizedEvent) onEvent(normalizedEvent)
  }
}
