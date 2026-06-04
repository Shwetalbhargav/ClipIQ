const YOUTUBE_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'])
const INSTAGRAM_HOSTS = new Set(['instagram.com', 'www.instagram.com'])

function getUrl(value) {
  try {
    return new URL(value.trim())
  } catch {
    return null
  }
}

export function isYouTubeVideoUrl(value) {
  const url = getUrl(value)
  if (!url || !YOUTUBE_HOSTS.has(url.hostname)) return false
  if (url.hostname === 'youtu.be') return url.pathname.split('/').filter(Boolean).length === 1
  return url.pathname === '/watch' && Boolean(url.searchParams.get('v'))
}

export function isInstagramReelUrl(value) {
  const url = getUrl(value)
  if (!url || !INSTAGRAM_HOSTS.has(url.hostname)) return false
  const parts = url.pathname.split('/').filter(Boolean)
  return parts.length >= 2 && (parts[0] === 'reel' || parts[0] === 'reels') && Boolean(parts[1])
}

export function validateComparisonUrls({ youtubeUrl, instagramUrl }) {
  const errors = {}

  if (!youtubeUrl.trim()) {
    errors.youtubeUrl = 'Enter one YouTube video URL.'
  } else if (!isYouTubeVideoUrl(youtubeUrl)) {
    errors.youtubeUrl = 'Use a supported YouTube video URL, not a playlist, channel, or generic link.'
  }

  if (!instagramUrl.trim()) {
    errors.instagramUrl = 'Enter one Instagram Reel URL.'
  } else if (!isInstagramReelUrl(instagramUrl)) {
    errors.instagramUrl = 'Use an Instagram Reel URL. Posts, profiles, and other platforms are not supported.'
  }

  return errors
}
