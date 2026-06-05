import { requestJson } from './client.js'

function normalizeVideo(video, fallbackLabel, fallbackPlatform) {
  if (!video) return null

  return {
    label: video.label || fallbackLabel,
    platform: video.platform || fallbackPlatform,
    videoId: video.video_id || null,
    sourceUrl: video.source_url || null,
    canonicalUrl: video.canonical_url || null,
    creator: video.creator || null,
    followerCount: video.follower_count ?? null,
    title: video.title || null,
    caption: video.caption || null,
    views: video.views ?? null,
    likes: video.likes ?? null,
    comments: video.comments ?? null,
    engagementRate: video.engagement_rate ?? null,
    hashtags: Array.isArray(video.hashtags) ? video.hashtags : [],
    uploadDate: video.upload_date || null,
    durationSeconds: video.duration_seconds ?? null,
    thumbnailUrl: video.thumbnail_url || null,
    transcriptStatus: video.transcript_status || 'unavailable',
    chunkCount: video.chunk_count ?? null,
    indexedChunkCount: video.indexed_chunk_count ?? null,
    unavailableReason: video.unavailable_reason || video.error_message || null,
  }
}

function findVideoError(errors, platform) {
  return errors.find((error) => error?.platform === platform) || null
}

export function normalizeComparison(payload) {
  if (!payload || typeof payload !== 'object' || !payload.comparison_id) {
    throw new Error('Invalid comparison payload.')
  }

  const errors = Array.isArray(payload.errors) ? payload.errors : []
  const videoA = normalizeVideo(payload.video_a, 'A', 'youtube')
  const videoB = normalizeVideo(payload.video_b, 'B', 'instagram')

  return {
    id: payload.comparison_id,
    status: payload.status || 'failed',
    videoA: videoA ? { ...videoA, extractionError: findVideoError(errors, 'youtube') } : null,
    videoB: videoB ? { ...videoB, extractionError: findVideoError(errors, 'instagram') } : null,
    transcriptStatus: payload.transcript_status || {},
    indexingStatus: payload.indexing_status || {},
    engagement: payload.engagement || {},
    errors,
    createdAt: payload.created_at || null,
    updatedAt: payload.updated_at || null,
  }
}

export async function createComparison({ youtubeUrl, instagramUrl }) {
  const payload = await requestJson('/comparisons', {
    method: 'POST',
    body: JSON.stringify({
      youtube_url: youtubeUrl,
      instagram_url: instagramUrl,
    }),
  })

  return normalizeComparison(payload)
}

export async function getComparison(comparisonId) {
  const payload = await requestJson(`/comparisons/${encodeURIComponent(comparisonId)}`)
  return normalizeComparison(payload)
}
