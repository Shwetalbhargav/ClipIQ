import { COMPARISON_STATUSES } from '../constants/app.js'
import { invalidPayloadError, requestJson } from './client.js'

const VALID_STATUSES = new Set(Object.values(COMPARISON_STATUSES))

function nullableString(value) {
  return typeof value === 'string' && value.trim() ? value : null
}

function nullableNumber(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function normalizeStatus(status) {
  return VALID_STATUSES.has(status) ? status : COMPARISON_STATUSES.failed
}

function normalizeVideo(video, fallbackLabel, fallbackPlatform) {
  if (!video || typeof video !== 'object') return null

  return {
    label: video.label === 'A' || video.label === 'B' ? video.label : fallbackLabel,
    platform: video.platform === 'youtube' || video.platform === 'instagram' ? video.platform : fallbackPlatform,
    videoId: nullableString(video.video_id),
    sourceUrl: nullableString(video.source_url),
    canonicalUrl: nullableString(video.canonical_url),
    creator: nullableString(video.creator),
    followerCount: nullableNumber(video.follower_count),
    title: nullableString(video.title),
    caption: nullableString(video.caption),
    views: nullableNumber(video.views),
    likes: nullableNumber(video.likes),
    comments: nullableNumber(video.comments),
    engagementRate: nullableNumber(video.engagement_rate),
    hashtags: Array.isArray(video.hashtags) ? video.hashtags.filter((tag) => typeof tag === 'string') : [],
    uploadDate: nullableString(video.upload_date),
    durationSeconds: nullableNumber(video.duration_seconds),
    thumbnailUrl: nullableString(video.thumbnail_url),
    transcriptStatus: nullableString(video.transcript_status) || 'unavailable',
    chunkCount: nullableNumber(video.chunk_count),
    indexedChunkCount: nullableNumber(video.indexed_chunk_count),
  }
}

function normalizeStatusMap(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}

  return Object.fromEntries(
    Object.entries(value)
      .filter(([label]) => label === 'A' || label === 'B')
      .map(([label, status]) => [label, nullableString(status) || 'unavailable']),
  )
}

function normalizeBackendIssue(issue, index) {
  if (typeof issue === 'string') {
    return { code: `issue_${index + 1}`, message: issue }
  }

  if (!issue || typeof issue !== 'object') {
    return { code: `issue_${index + 1}`, message: 'Processing issue unavailable.' }
  }

  return {
    code: nullableString(issue.code) || `issue_${index + 1}`,
    message: nullableString(issue.message) || nullableString(issue.detail) || 'Processing issue unavailable.',
  }
}

export function normalizeComparison(payload, { endpoint = null } = {}) {
  if (!payload || typeof payload !== 'object' || !nullableString(payload.comparison_id)) {
    throw invalidPayloadError('The backend returned an invalid comparison payload.', { endpoint, payload })
  }

  return {
    id: payload.comparison_id,
    status: normalizeStatus(payload.status),
    videoA: normalizeVideo(payload.video_a, 'A', 'youtube'),
    videoB: normalizeVideo(payload.video_b, 'B', 'instagram'),
    transcriptStatus: normalizeStatusMap(payload.transcript_status),
    indexingStatus: normalizeStatusMap(payload.indexing_status),
    engagement: {
      summary: nullableString(payload.engagement?.summary),
    },
    errors: Array.isArray(payload.errors) ? payload.errors.map(normalizeBackendIssue) : [],
    createdAt: nullableString(payload.created_at),
    updatedAt: nullableString(payload.updated_at),
  }
}

export async function createComparison({ youtubeUrl, instagramUrl }) {
  const endpoint = '/comparisons'
  const payload = await requestJson(endpoint, {
    method: 'POST',
    body: JSON.stringify({
      youtube_url: youtubeUrl,
      instagram_url: instagramUrl,
    }),
  })

  return normalizeComparison(payload, { endpoint })
}

export async function getComparison(comparisonId) {
  const endpoint = `/comparisons/${encodeURIComponent(comparisonId)}`
  const payload = await requestJson(endpoint)
  return normalizeComparison(payload, { endpoint })
}
