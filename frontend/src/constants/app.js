export const APP_NAME = 'ClipIQ'

export const LOCAL_API_BASE_URL = 'http://localhost:8000/api'
export const RENDER_API_BASE_URL = 'https://clipiq-bmpu.onrender.com/api'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || RENDER_API_BASE_URL

export const ROUTES = {
  create: '/',
  history: '/history',
  comparison: (comparisonId) => `/comparisons/${comparisonId}`,
}

export const VIDEO_LABELS = {
  youtube: 'Video A',
  instagram: 'Video B',
}

export const COMPARISON_STATUSES = {
  ready: 'ready',
  partial: 'partial',
  failed: 'failed',
}

export const UNAVAILABLE_LABEL = 'Unavailable'
