import { Loader2 } from 'lucide-react'

const variantClasses = {
  primary: 'bg-primary text-on-primary hover:brightness-105 disabled:hover:brightness-100',
  secondary: 'border border-outline-variant bg-surface-container text-on-surface hover:bg-surface-container-high',
  ghost: 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface',
  danger: 'border border-error/40 bg-error/10 text-error hover:bg-error/15',
}

const sizeClasses = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-3 text-sm',
  lg: 'h-12 px-4 text-sm',
  icon: 'h-10 w-10',
}

function Button({
  children,
  className = '',
  disabled = false,
  icon: Icon,
  isLoading = false,
  size = 'md',
  type = 'button',
  variant = 'secondary',
  ...props
}) {
  return (
    <button
      type={type}
      className={`inline-flex shrink-0 items-center justify-center gap-2 rounded-lg font-bold outline-none transition disabled:cursor-not-allowed disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-primary/70 ${variantClasses[variant] || variantClasses.secondary} ${sizeClasses[size] || sizeClasses.md} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : Icon ? <Icon className="h-4 w-4" aria-hidden="true" /> : null}
      {children}
    </button>
  )
}

export default Button
