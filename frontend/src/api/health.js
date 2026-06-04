import { requestJson } from './client.js'

export function normalizeHealth(payload) {
  return {
    status: payload?.status || 'unknown',
    service: payload?.service || 'ClipIQ',
    environment: payload?.environment || null,
    services: payload?.services || {},
  }
}

export async function getHealth() {
  const payload = await requestJson('/health')
  return normalizeHealth(payload)
}
