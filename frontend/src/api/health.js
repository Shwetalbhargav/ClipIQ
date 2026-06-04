import { invalidPayloadError, requestJson } from './client.js'

function normalizeServiceStatus(value) {
  return typeof value === 'string' && value.trim() ? value : 'unknown'
}

export function normalizeHealth(payload, { endpoint = null } = {}) {
  if (!payload || typeof payload !== 'object') {
    throw invalidPayloadError('The backend returned an invalid health payload.', { endpoint, payload })
  }

  const services = payload.services && typeof payload.services === 'object' && !Array.isArray(payload.services)
    ? Object.fromEntries(Object.entries(payload.services).map(([name, status]) => [name, normalizeServiceStatus(status)]))
    : {}

  return {
    status: normalizeServiceStatus(payload.status),
    service: typeof payload.service === 'string' && payload.service.trim() ? payload.service : 'ClipIQ',
    environment: typeof payload.environment === 'string' && payload.environment.trim() ? payload.environment : null,
    services,
  }
}

export async function getHealth() {
  const endpoint = '/health'
  const payload = await requestJson(endpoint)
  return normalizeHealth(payload, { endpoint })
}
