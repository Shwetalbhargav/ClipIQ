import { Activity } from 'lucide-react'

function Logo({ compact = false }) {
  return (
    <span className="flex items-center gap-3">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-primary/45 bg-surface-container-high text-primary">
        <Activity className="h-5 w-5" aria-hidden="true" />
      </span>
      {!compact && (
        <span className="min-w-0">
          <span className="block text-lg font-bold leading-5 text-on-surface">ClipIQ</span>
          <span className="block text-xs text-on-surface-variant">RAG comparison</span>
        </span>
      )}
    </span>
  )
}

export default Logo
