import { useEffect, useState } from 'react'
import { getHealth } from '../api/health.js'

function resolveHealthStatus(data) {
  if (!data) return 'offline'
  const serviceValues = Object.values(data.services || {})
  const hasServiceIssue = serviceValues.some((value) => value && String(value).toLowerCase() !== 'ok')
  if (data.status === 'ok' && !hasServiceIssue) return 'online'
  return 'degraded'
}

export function useHealth() {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })

  useEffect(() => {
    let active = true

    getHealth()
      .then((data) => {
        if (active) setState({ status: resolveHealthStatus(data), data, error: null })
      })
      .catch((error) => {
        if (active) setState({ status: 'offline', data: null, error })
      })

    return () => {
      active = false
    }
  }, [])

  return state
}
