import { History, Home } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { APP_NAME, ROUTES } from '../../constants/app.js'
import { useHealth } from '../../hooks/useHealth.js'
import { useTheme } from '../../hooks/useTheme.js'
import Logo from '../ui/Logo.jsx'
import StatusBadge from '../ui/StatusBadge.jsx'
import ThemeToggle from '../ui/ThemeToggle.jsx'

const navItems = [
  { to: ROUTES.create, label: 'Create', icon: Home },
  { to: ROUTES.history, label: 'History', icon: History },
]

function navClass({ isActive }) {
  return [
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-primary/70',
    isActive
      ? 'bg-surface-container-highest text-on-surface'
      : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface',
  ].join(' ')
}

function AppShell({ children }) {
  const health = useHealth()
  const { isDark, toggleTheme } = useTheme()

  const healthLabel =
    health.status === 'online' ? 'Backend Online' : health.status === 'loading' ? 'Checking Backend' : 'Backend Offline'
  const healthTone = health.status === 'online' ? 'ready' : health.status === 'loading' ? 'neutral' : 'offline'

  return (
    <div className="min-h-screen bg-background text-on-surface">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[260px] border-r border-outline-variant bg-surface-container-low px-4 py-5 lg:block">
        <NavLink to={ROUTES.create} className="mb-8 block rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-primary/70" aria-label={`${APP_NAME} home`}>
          <Logo />
        </NavLink>

        <nav aria-label="Primary" className="space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={navClass}>
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="absolute bottom-5 left-4 right-4 space-y-3">
          <StatusBadge tone={healthTone} label={healthLabel} />
          <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-outline-variant bg-surface/95 px-4 backdrop-blur lg:hidden">
        <NavLink to={ROUTES.create} className="rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-primary/70" aria-label={`${APP_NAME} home`}>
          <Logo compact />
        </NavLink>
        <div className="flex items-center gap-2">
          <StatusBadge tone={healthTone} label={health.status === 'online' ? 'Online' : 'Offline'} />
          <ThemeToggle compact isDark={isDark} onToggle={toggleTheme} />
        </div>
      </header>

      <main className="min-w-0 pb-24 lg:ml-[260px] lg:pb-0">{children}</main>

      <nav aria-label="Primary" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-2 border-t border-outline-variant bg-surface-container-low px-3 py-2 lg:hidden">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `flex flex-col items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-primary/70 ${isActive ? 'text-primary' : 'text-on-surface-variant'}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

export default AppShell
