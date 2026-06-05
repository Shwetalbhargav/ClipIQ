import { useEffect, useState } from 'react'
import { getComparison } from '../api/comparisons.js'
import { COMPARISON_STATUSES } from '../constants/app.js'

const TERMINAL_STATUSES = new Set([
  COMPARISON_STATUSES.ready,
  COMPARISON_STATUSES.partial,
  COMPARISON_STATUSES.failed,
])

export function isTerminalComparisonStatus(status) {
  return TERMINAL_STATUSES.has(status)
}

export function useComparisonPolling(comparisonId, { initialComparison = null, intervalMs = 2500 } = {}) {
  const [state, setState] = useState({
    comparison: initialComparison,
    error: null,
    isPolling: Boolean(comparisonId && !isTerminalComparisonStatus(initialComparison?.status)),
  })

  useEffect(() => {
    if (!comparisonId) return undefined

    let active = true
    let timerId

    async function poll() {
      setState((current) => ({ ...current, isPolling: true, error: null }))

      try {
        const comparison = await getComparison(comparisonId)
        if (!active) return

        const isTerminal = isTerminalComparisonStatus(comparison.status)
        setState({ comparison, error: null, isPolling: !isTerminal })

        if (!isTerminal) {
          timerId = window.setTimeout(poll, intervalMs)
        }
      } catch (error) {
        if (!active) return
        setState((current) => ({ ...current, error, isPolling: false }))
      }
    }

    if (isTerminalComparisonStatus(initialComparison?.status)) {
      setState({ comparison: initialComparison, error: null, isPolling: false })
      return undefined
    }

    poll()

    return () => {
      active = false
      if (timerId) window.clearTimeout(timerId)
    }
  }, [comparisonId, initialComparison, intervalMs])

  return state
}
