import { UNAVAILABLE_LABEL } from '../constants/app.js'

const compactNumberFormatter = new Intl.NumberFormat('en', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat('en', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

export function formatUnavailable(value) {
  return value === null || value === undefined || value === '' ? UNAVAILABLE_LABEL : value
}

export function formatNumber(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return UNAVAILABLE_LABEL
  return compactNumberFormatter.format(value)
}

export function formatPercent(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return UNAVAILABLE_LABEL
  return `${value.toFixed(value >= 10 ? 1 : 2)}%`
}

export function formatSeconds(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return UNAVAILABLE_LABEL
  const minutes = Math.floor(value / 60)
  const seconds = Math.floor(value % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function formatDate(value) {
  if (!value) return UNAVAILABLE_LABEL
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return UNAVAILABLE_LABEL
  return dateFormatter.format(date)
}

export function formatTimestampRange(startSeconds, endSeconds) {
  if (typeof startSeconds !== 'number' || typeof endSeconds !== 'number') return UNAVAILABLE_LABEL
  return `${formatSeconds(startSeconds)}-${formatSeconds(endSeconds)}`
}
