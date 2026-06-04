import { Moon, Sun } from 'lucide-react'

function ThemeToggle({ compact = false, isDark, onToggle }) {
  const label = isDark ? 'Switch to light theme' : 'Switch to dark theme'
  const Icon = isDark ? Moon : Sun

  if (compact) {
    return (
      <button
        type="button"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-outline-variant bg-surface-container text-on-surface outline-none transition-colors hover:bg-surface-container-high focus-visible:ring-2 focus-visible:ring-primary/70"
        onClick={onToggle}
        aria-label={label}
        aria-pressed={!isDark}
      >
        <Icon className="h-4 w-4" aria-hidden="true" />
      </button>
    )
  }

  return (
    <button
      type="button"
      className="flex h-10 w-full min-w-[8.5rem] items-center justify-between rounded-lg border border-outline-variant bg-surface-container px-3 text-sm font-semibold text-on-surface outline-none transition-colors hover:bg-surface-container-high focus-visible:ring-2 focus-visible:ring-primary/70"
      onClick={onToggle}
      aria-label={label}
      aria-pressed={!isDark}
    >
      Theme
      <Icon className="h-4 w-4" aria-hidden="true" />
    </button>
  )
}

export default ThemeToggle
