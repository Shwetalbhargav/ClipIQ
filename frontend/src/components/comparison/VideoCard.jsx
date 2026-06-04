import { Clapperboard, PlaySquare } from 'lucide-react'
import { resolveEngagementRate } from '../../utils/engagement.js'
import { formatDate, formatNumber, formatPercent, formatSeconds, formatUnavailable } from '../../utils/formatters.js'
import MetricRow from './MetricRow.jsx'

function VideoCard({ video }) {
  if (!video) {
    return (
      <section className="rounded-xl border border-outline-variant bg-surface-container p-4">
        <p className="text-sm font-semibold text-on-surface">Video data unavailable</p>
        <p className="mt-2 text-sm text-on-surface-variant">The backend did not return this side of the comparison.</p>
      </section>
    )
  }

  const isYouTube = video.platform === 'youtube'
  const Icon = isYouTube ? PlaySquare : Clapperboard
  const accent = isYouTube ? 'text-primary' : 'text-secondary'
  const title = video.title || video.caption

  return (
    <section className="min-w-0 rounded-xl border border-outline-variant bg-surface-container">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant bg-surface-container-high px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <Icon className={`h-5 w-5 shrink-0 ${accent}`} aria-hidden="true" />
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-on-surface">
              Video {video.label} · {isYouTube ? 'YouTube' : 'Instagram Reel'}
            </h2>
            <p className="truncate text-sm text-on-surface-variant">{formatUnavailable(video.creator)}</p>
          </div>
        </div>
        <span className={`rounded-full border border-current/30 px-2 py-1 text-xs font-semibold ${accent}`}>
          {formatUnavailable(video.transcriptStatus)}
        </span>
      </div>

      <div className="space-y-4 p-4">
        {video.thumbnailUrl ? (
          <img
            src={video.thumbnailUrl}
            alt={`Thumbnail for Video ${video.label}`}
            className="aspect-video w-full rounded-xl border border-outline-variant object-cover"
          />
        ) : (
          <div className="flex aspect-video w-full items-center justify-center rounded-xl border border-dashed border-outline-variant bg-surface-container-low text-sm text-on-surface-variant">
            Thumbnail unavailable
          </div>
        )}

        <div>
          <p className="line-clamp-2 text-sm font-semibold text-on-surface">{formatUnavailable(title)}</p>
          <p className="mt-1 truncate text-xs text-on-surface-variant">{formatUnavailable(video.canonicalUrl || video.sourceUrl)}</p>
        </div>

        <dl>
          <MetricRow label="Views" value={formatNumber(video.views)} />
          <MetricRow label="Likes" value={formatNumber(video.likes)} />
          <MetricRow label="Comments" value={formatNumber(video.comments)} />
          <MetricRow label="Followers" value={formatNumber(video.followerCount)} />
          <MetricRow label="Engagement" value={formatPercent(resolveEngagementRate(video))} />
          <MetricRow label="Duration" value={formatSeconds(video.durationSeconds)} />
          <MetricRow label="Uploaded" value={formatDate(video.uploadDate)} />
          <MetricRow label="Chunks" value={typeof video.chunkCount === 'number' ? `${video.indexedChunkCount ?? 0}/${video.chunkCount}` : null} />
        </dl>
      </div>
    </section>
  )
}

export default VideoCard
