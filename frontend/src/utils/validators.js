const YOUTUBE_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'])
const INSTAGRAM_HOSTS = new Set(['instagram.com', 'www.instagram.com'])
const TIKTOK_HOSTS = new Set(['tiktok.com', 'www.tiktok.com', 'm.tiktok.com'])

function getUrl(value) {
  try {
    return new URL(value.trim())
  } catch {
    return null
  }
}

function hostname(url) {
  return url?.hostname.toLowerCase().replace(/^www\./, 'www.')
}

export function isYouTubeVideoUrl(value) {
  const url = getUrl(value)
  if (!url || !YOUTUBE_HOSTS.has(hostname(url))) return false
  if (hostname(url) === 'youtu.be') return url.pathname.split('/').filter(Boolean).length === 1
  return url.pathname === '/watch' && Boolean(url.searchParams.get('v'))
}

export function isInstagramReelUrl(value) {
  const url = getUrl(value)
  if (!url || !INSTAGRAM_HOSTS.has(hostname(url))) return false
  const parts = url.pathname.split('/').filter(Boolean)
  return parts.length >= 2 && (parts[0] === 'reel' || parts[0] === 'reels') && Boolean(parts[1])
}

function isTikTokUrl(value) {
  const url = getUrl(value)
  return Boolean(url && TIKTOK_HOSTS.has(hostname(url)))
}

function isInstagramPostUrl(value) {
  const url = getUrl(value)
  if (!url || !INSTAGRAM_HOSTS.has(hostname(url))) return false
  return url.pathname.split('/').filter(Boolean)[0] === 'p'
}

export function validateComparisonUrls({ youtubeUrl, instagramUrl }) {
  const errors = {}

  if (!youtubeUrl.trim()) {
    errors.youtubeUrl = 'Enter one YouTube video URL.'
  } else if (isTikTokUrl(youtubeUrl)) {
    errors.youtubeUrl = 'TikTok is not supported. Video A must be a YouTube watch URL.'
  } else if (!isYouTubeVideoUrl(youtubeUrl)) {
    errors.youtubeUrl = 'Use a YouTube watch URL with a video id, not a playlist, channel, Shorts, or generic link.'
  }

  if (!instagramUrl.trim()) {
    errors.instagramUrl = 'Enter one Instagram Reel URL.'
  } else if (isTikTokUrl(instagramUrl)) {
    errors.instagramUrl = 'TikTok is not supported. Video B must be an Instagram Reel URL.'
  } else if (isInstagramPostUrl(instagramUrl)) {
    errors.instagramUrl = 'Instagram posts are not supported. Use an Instagram /reel/ or /reels/ URL.'
  } else if (!isInstagramReelUrl(instagramUrl)) {
    errors.instagramUrl = 'Use an Instagram Reel URL. Posts, profiles, and other platforms are not supported.'
  }

  return errors
}

export function getFirstComparisonUrlErrorField(errors) {
  if (errors.youtubeUrl) return 'youtube-url'
  if (errors.instagramUrl) return 'instagram-url'
  return null
}
