import { forwardRef } from 'react'

const UrlInput = forwardRef(function UrlInput({
  disabled = false,
  error,
  icon: Icon,
  id,
  label,
  onChange,
  placeholder,
  required = false,
  tone = 'primary',
  value,
}, ref) {
  const errorId = `${id}-error`
  const focusTone = tone === 'secondary' ? 'focus-within:ring-secondary/70' : 'focus-within:ring-primary/70'
  const iconTone = error ? 'text-error' : tone === 'secondary' ? 'text-secondary' : 'text-primary'

  return (
    <label className="block" htmlFor={id}>
      <span className="flex items-center justify-between gap-3 text-sm font-semibold text-on-surface">
        {label}
        {required && <span className="text-xs font-semibold uppercase tracking-[0.18em] text-on-surface-variant">Required</span>}
      </span>
      <span className={`mt-2 flex min-h-12 items-center gap-3 rounded-lg border bg-surface-container-lowest px-3 py-3 transition focus-within:ring-2 ${disabled ? 'opacity-60' : ''} ${error ? 'border-error' : 'border-outline-variant'} ${focusTone}`}>
        {Icon && <Icon className={`h-5 w-5 shrink-0 ${iconTone}`} aria-hidden="true" />}
        <input
          id={id}
          ref={ref}
          type="url"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none placeholder:text-outline"
          aria-describedby={errorId}
          aria-invalid={Boolean(error)}
        />
      </span>
      <span id={errorId} aria-live="polite" className={`mt-2 block min-h-5 text-sm font-semibold ${error ? 'text-error' : 'text-transparent'}`}>
        {error || ''}
      </span>
    </label>
  )
})

export default UrlInput
