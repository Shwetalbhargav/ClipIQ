import StatusBadge from './StatusBadge.jsx'

function healthPresentation(status) {
  if (status === 'online') return { label: 'Backend Online', mobileLabel: 'Online', tone: 'ready' }
  if (status === 'degraded') return { label: 'Service Degraded', mobileLabel: 'Degraded', tone: 'partial' }
  if (status === 'loading') return { label: 'Checking Backend', mobileLabel: 'Checking', tone: 'neutral' }
  return { label: 'Backend Offline', mobileLabel: 'Offline', tone: 'offline' }
}

function HealthBadge({ compact = false, status }) {
  const presentation = healthPresentation(status)
  return <StatusBadge tone={presentation.tone} label={compact ? presentation.mobileLabel : presentation.label} />
}

export default HealthBadge
