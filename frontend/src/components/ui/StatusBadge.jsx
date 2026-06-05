const toneClasses = {
  ready: 'border-tertiary/40 bg-tertiary/10 text-tertiary',
  partial: 'border-warning/40 bg-warning/10 text-warning',
  failed: 'border-error/40 bg-error/10 text-error',
  offline: 'border-error/40 bg-error/10 text-error',
  degraded: 'border-warning/40 bg-warning/10 text-warning',
  neutral: 'border-outline-variant bg-surface-container-high text-on-surface-variant',
}

function StatusBadge({ className = '', tone = 'neutral', label }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClasses[tone] || toneClasses.neutral} ${className}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {label}
    </span>
  )
}

export default StatusBadge
