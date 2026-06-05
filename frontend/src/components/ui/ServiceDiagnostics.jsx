import { AlertTriangle, Database, ServerCrash } from 'lucide-react'
import { UNAVAILABLE_LABEL } from '../../constants/app.js'
import Card from './Card.jsx'
import StatusBadge from './StatusBadge.jsx'

const serviceLabels = {
  mongodb: 'MongoDB',
  qdrant: 'Qdrant',
}

function serviceTone(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'ok' || normalized === 'active' || normalized === 'online') return 'ready'
  if (!value) return 'neutral'
  return 'failed'
}

function serviceLabel(value) {
  if (!value) return UNAVAILABLE_LABEL
  return String(value).replaceAll('_', ' ')
}

function ServiceDiagnostics({ health }) {
  const services = health.data?.services || {}
  const knownServices = Object.keys(serviceLabels)
  const hasServiceData = knownServices.some((key) => services[key])
  const isHealthy = health.status === 'online'
  const isLoading = health.status === 'loading'

  return (
    <Card as="aside" className="p-5">
      <div className="flex items-start gap-3">
        {isHealthy ? (
          <Database className="mt-0.5 h-5 w-5 shrink-0 text-tertiary" aria-hidden="true" />
        ) : (
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-error" aria-hidden="true" />
        )}
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-on-surface">
            {isHealthy ? 'Service diagnostics' : 'Service availability warning'}
          </h2>
          <p className="mt-2 text-sm leading-6 text-on-surface-variant">
            {isHealthy
              ? 'Backend health is available. Source extraction can still fail if platforms require login or rate-limit access.'
              : 'You can keep editing URLs, but comparison creation may fail until the backend health check recovers.'}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        {knownServices.map((key) => (
          <div key={key} className="rounded-lg border border-outline-variant bg-surface-container-lowest p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-semibold text-on-surface">{serviceLabels[key]}</span>
              <StatusBadge tone={serviceTone(services[key])} label={serviceLabel(services[key])} />
            </div>
          </div>
        ))}
      </div>

      {!hasServiceData && (
        <div className="mt-4 flex gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-3 text-sm text-on-surface-variant">
          <ServerCrash className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {isLoading ? 'Waiting for health details from the backend.' : 'Service-level diagnostics were not returned by the backend.'}
        </div>
      )}

      {health.error && (
        <p className="mt-4 text-sm leading-6 text-error">
          {health.error.message || 'Network error while checking backend health.'}
        </p>
      )}
    </Card>
  )
}

export default ServiceDiagnostics
