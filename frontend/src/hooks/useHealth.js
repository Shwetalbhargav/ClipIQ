import { useEffect, useState } from 'react'
import { getHealth } from '../api/health.js'

export function useHealth() {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })

  useEffect(() => {
    let active = true

    getHealth()
      .then((data) => {
        if (active) setState({ status: data.status === 'ok' ? 'online' : 'degraded', data, error: null })
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
