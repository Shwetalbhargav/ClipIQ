import { API_BASE_URL } from '../constants/app.js'

export const API_ERROR_TYPES = {
  invalidPayload: 'invalid_payload',
  network: 'network',
  notFound: 'not_found',
  serviceUnavailable: 'service_unavailable',
  validation: 'validation',
  unknown: 'unknown',
}

export class ApiError extends Error {
  constructor(message, { details = null, endpoint = null, payload = null, status = null, type = API_ERROR_TYPES.unknown } = {}) {
    super(message)
    this.name = 'ApiError'
    this.details = details
    this.endpoint = endpoint
    this.payload = payload
    this.status = status
    this.type = type
  }
}

function trimTrailingSlash(value) {
  return value.replace(/\/$/, '')
}

function normalizePath(path) {
  return path.startsWith('/') ? path : `/${path}`
}

function buildUrl(path) {
  return `${trimTrailingSlash(API_BASE_URL)}${normalizePath(path)}`
}

function errorTypeForStatus(status) {
  if (status === 404) return API_ERROR_TYPES.notFound
  if (status === 422) return API_ERROR_TYPES.validation
  if (status === 503) return API_ERROR_TYPES.serviceUnavailable
  return API_ERROR_TYPES.unknown
}

function detailToMessage(detail) {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const firstMessage = detail.find((item) => typeof item?.msg === 'string')?.msg
    return firstMessage || null
  }
  if (typeof detail?.message === 'string') return detail.message
  if (typeof detail?.error === 'string') return detail.error
  return null
}

function friendlyMessage(status, payload) {
  const detailMessage = detailToMessage(payload?.detail || payload?.error || payload?.message)
  if (detailMessage) return detailMessage
  if (status === 404) return 'The requested comparison was not found.'
  if (status === 422) return 'The request was rejected. Check both URLs and try again.'
  if (status === 503) return 'The backend service is unavailable right now.'
  return 'The request failed. Please try again.'
}

export function invalidPayloadError(message, { endpoint = null, payload = null } = {}) {
  return new ApiError(message, {
    endpoint,
    payload,
    type: API_ERROR_TYPES.invalidPayload,
  })
}

export function normalizeUnknownError(error, fallbackMessage = 'The request failed. Please try again.') {
  if (error instanceof ApiError) return error
  return new ApiError(error?.message || fallbackMessage, {
    details: error || null,
    type: API_ERROR_TYPES.unknown,
  })
}

export function isNotFoundError(error) {
  return error?.type === API_ERROR_TYPES.notFound || error?.status === 404
}

export async function requestJson(path, options = {}) {
  const endpoint = buildUrl(path)
  let response

  try {
    response = await fetch(endpoint, {
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
      endpoint,
      type: API_ERROR_TYPES.network,
    })
  }

  const text = await response.text()
  let payload = null

  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw invalidPayloadError('The backend returned an invalid JSON payload.', {
        endpoint,
        payload: text,
      })
    }
  }

  if (!response.ok) {
    throw new ApiError(friendlyMessage(response.status, payload), {
      endpoint,
      payload,
      status: response.status,
      type: errorTypeForStatus(response.status),
    })
  }

  return payload
}

export function apiUrl(path) {
  return buildUrl(path)
}
