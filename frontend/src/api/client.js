import { API_BASE_URL } from '../constants/app.js'

export class ApiError extends Error {
  constructor(message, { status, details } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

function buildUrl(path) {
  return `${API_BASE_URL.replace(/\/$/, '')}${path}`
}

function friendlyMessage(status, fallback) {
  if (status === 404) return 'The requested comparison was not found.'
  if (status === 422) return 'The request was rejected. Check both URLs and try again.'
  if (status === 503) return 'The backend service is unavailable right now.'
  return fallback || 'The request failed. Please try again.'
}

export async function requestJson(path, options = {}) {
  let response

  try {
    response = await fetch(buildUrl(path), {
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })
  } catch (error) {
    throw new ApiError('Network error. Confirm the backend is running and reachable.', {
      details: error,
    })
  }

  let payload = null
  const text = await response.text()
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw new ApiError('The backend returned an invalid JSON payload.', {
        status: response.status,
        details: text,
      })
    }
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.error || payload?.message
    throw new ApiError(Array.isArray(detail) ? friendlyMessage(response.status) : friendlyMessage(response.status, detail), {
      status: response.status,
      details: payload,
    })
  }

  return payload
}

export function apiUrl(path) {
  return buildUrl(path)
}
