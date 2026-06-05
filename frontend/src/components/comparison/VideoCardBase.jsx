import Card, { CardBody, CardHeader } from '../ui/Card.jsx'
import UnavailableValue from '../ui/UnavailableValue.jsx'

function VideoCardBase({
  accentClassName = 'text-primary',
  children,
  creator,
  icon: Icon,
  label,
  platform,
  status,
  thumbnailAlt,
  thumbnailUrl,
}) {
  return (
    <Card className="min-w-0 overflow-hidden">
      <CardHeader className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          {Icon && <Icon className={`h-5 w-5 shrink-0 ${accentClassName}`} aria-hidden="true" />}
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-on-surface">
              {label} - {platform}
            </h2>
            <UnavailableValue value={creator} className="block truncate text-sm text-on-surface-variant" />
          </div>
        </div>
        {status && (
          <span className={`rounded-full border border-current/30 px-2 py-1 text-xs font-semibold ${accentClassName}`}>
            {status}
          </span>
        )}
      </CardHeader>

      <CardBody className="space-y-4">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={thumbnailAlt}
            className="aspect-video w-full rounded-xl border border-outline-variant object-cover"
          />
        ) : (
          <div className="flex aspect-video w-full items-center justify-center rounded-xl border border-dashed border-outline-variant bg-surface-container-low text-sm text-on-surface-variant">
            Thumbnail unavailable
          </div>
        )}
        {children}
      </CardBody>
    </Card>
  )
}

export default VideoCardBase
