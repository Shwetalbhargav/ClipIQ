import { AlertCircle } from 'lucide-react'

function ErrorAlert({ children, className = '', title }) {
  return (
    <div className={`flex gap-2 rounded-lg border border-error/40 bg-error/10 p-3 text-sm text-error ${className}`} role="alert">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? 'mt-1' : ''}>{children}</div>
      </div>
    </div>
  )
}

export default ErrorAlert
