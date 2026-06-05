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

export function compareEngagement(videoA, videoB) {
  const rateA = resolveEngagementRate(videoA)
  const rateB = resolveEngagementRate(videoB)

  if (typeof rateA !== 'number' || typeof rateB !== 'number') {
    return { winner: null, rateA, rateB, delta: null }
  }

  if (rateA === rateB) {
    return { winner: 'tie', rateA, rateB, delta: 0 }
  }

  return {
    winner: rateA > rateB ? 'A' : 'B',
    rateA,
    rateB,
    delta: Math.abs(rateA - rateB),
  }
}
