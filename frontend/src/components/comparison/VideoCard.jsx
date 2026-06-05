import { Clapperboard, PlaySquare } from 'lucide-react'
import { resolveEngagementRate } from '../../utils/engagement.js'
import { formatDate, formatNumber, formatPercent, formatSeconds } from '../../utils/formatters.js'
import Card from '../ui/Card.jsx'
import UnavailableValue from '../ui/UnavailableValue.jsx'
import MetricRow from './MetricRow.jsx'
import VideoCardBase from './VideoCardBase.jsx'

function statusValue(statusMap, label) {
  return statusMap?.[label] || statusMap?.[String(label).toUpperCase()] || null
}

function VideoCard({ fallbackLabel = 'Video', fallbackPlatform = 'Source', indexingStatus = {}, isWinner = false, reason, transcriptStatus = {}, video }) {
  if (!video) {
    return (
      <Card className="border-error/40 bg-error/5 p-4">
        <p className="text-sm font-semibold text-on-surface">{fallbackLabel} ({fallbackPlatform})</p>
        <p className="mt-2 text-sm text-on-surface-variant">The backend did not return this side of the comparison.</p>
        {reason && (
          <p className="mt-3 rounded-lg border border-error/30 bg-error/10 p-3 text-sm font-semibold text-error">
            {reason}
          </p>
        )}
      </Card>
    )
  }

  const isYouTube = video.platform === 'youtube'
  const Icon = isYouTube ? PlaySquare : Clapperboard
  const accent = isYouTube ? 'text-primary' : 'text-secondary'
  const title = video.title || video.caption

  return (
    <VideoCardBase
      icon={Icon}
      accentClassName={accent}
      label={`Video ${video.label}`}
      platform={isYouTube ? 'YouTube' : 'Instagram Reel'}
      creator={video.creator}
      status={video.transcriptStatus}
      thumbnailUrl={video.thumbnailUrl}
      thumbnailAlt={`Thumbnail for Video ${video.label}`}
      className={isWinner ? 'ring-2 ring-primary/60' : ''}
    >
      {(video.unavailableReason || video.extractionError?.message) && (
        <p className="rounded-lg border border-error/30 bg-error/10 p-3 text-sm font-semibold text-error">
          {video.unavailableReason || video.extractionError.message}
        </p>
      )}

      <div>
        <UnavailableValue as="p" value={title} className="line-clamp-2 text-sm font-semibold text-on-surface" />
        <UnavailableValue as="p" value={video.canonicalUrl || video.sourceUrl} className="mt-1 truncate text-xs text-on-surface-variant" />
      </div>

      <dl>
        <MetricRow label="Views" value={formatNumber(video.views)} />
        <MetricRow label="Likes" value={formatNumber(video.likes)} />
        <MetricRow label="Comments" value={formatNumber(video.comments)} />
        <MetricRow label="Followers" value={formatNumber(video.followerCount)} />
        <MetricRow label="Engagement" value={formatPercent(resolveEngagementRate(video))} />
        <MetricRow label="Duration" value={formatSeconds(video.durationSeconds)} />
        <MetricRow label="Uploaded" value={formatDate(video.uploadDate)} />
        <MetricRow label="Transcript" value={video.transcriptStatus || statusValue(transcriptStatus, video.label)} />
        <MetricRow label="Index" value={statusValue(indexingStatus, video.label)} />
        <MetricRow label="Chunks" value={typeof video.chunkCount === 'number' ? `${video.indexedChunkCount ?? 0}/${video.chunkCount}` : null} />
      </dl>
    </VideoCardBase>
  )
}

export default VideoCard
