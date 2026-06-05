import UnavailableValue from '../ui/UnavailableValue.jsx'

function MetricRow({ label, value }) {
  return (
    <div className="flex min-h-9 items-center justify-between gap-3 border-b border-outline-variant/70 py-2 last:border-0">
      <dt className="text-sm text-on-surface-variant">{label}</dt>
      <dd className="min-w-0 text-right text-sm font-semibold text-on-surface">
        <UnavailableValue value={value} />
      </dd>
    </div>
  )
}

export default MetricRow
