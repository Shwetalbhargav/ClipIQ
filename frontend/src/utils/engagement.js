export function calculateEngagementRate({ likes, comments, views }) {
  if (
    typeof likes !== 'number' ||
    typeof comments !== 'number' ||
    typeof views !== 'number' ||
    views <= 0
  ) {
    return null
  }

  return ((likes + comments) / views) * 100
}

export function resolveEngagementRate(video) {
  if (typeof video?.engagementRate === 'number') return video.engagementRate
  return calculateEngagementRate(video || {})
}
