import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  Moon,
  Sun,
  Upload,
  X,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'
import { authApi } from '../services/api'
import { Badge, cn } from './ui'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, end: true },
  { name: 'Fields', href: '/fields', icon: MapPin },
  { name: 'Wells', href: '/wells', icon: Activity },
  { name: 'Upload Data', href: '/upload', icon: Upload },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, setUser, logout } = useAuthStore()
  const { theme, toggle } = useThemeStore()
  const [mobileOpen, setMobileOpen] = useState(false)

  // Resolve the real identity once per session so role-gated controls render
  // correctly rather than assuming a role at login.
  useEffect(() => {
    if (user) return
    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => undefined)
  }, [user, setUser])

  // A route change should never leave the mobile drawer covering the page.
  useEffect(() => setMobileOpen(false), [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = (user?.full_name || user?.username || '?')
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const sidebar = (
    <>
      <div className="flex h-16 items-center gap-2.5 border-b border-edge px-5">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary-600 text-sm font-bold text-white">
          W
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-tight text-content">WOEnv</p>
          <p className="truncate text-2xs text-content-subtle">Operating Envelopes</p>
        </div>
        <button
          onClick={() => setMobileOpen(false)}
          className="ml-auto rounded-md p-1.5 text-content-muted hover:bg-surface-sunken lg:hidden"
          aria-label="Close navigation"
        >
          <X size={18} />
        </button>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navigation.map(({ name, href, icon: Icon, end }) => (
          <NavLink
            key={name}
            to={href}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-600/10 text-primary-700 dark:text-primary-300'
                  : 'text-content-muted hover:bg-surface-sunken hover:text-content',
              )
            }
          >
            <Icon className="h-4.5 w-4.5 shrink-0" size={18} />
            {name}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-edge p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-surface-sunken text-2xs font-semibold text-content-muted ring-1 ring-edge">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-content">
              {user?.full_name || user?.username || 'Signed in'}
            </p>
            {user?.role && (
              <Badge tone={user.role === 'admin' ? 'info' : 'neutral'} className="mt-1">
                {user.role}
              </Badge>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md p-1.5 text-content-subtle transition-colors hover:bg-surface-sunken hover:text-breach"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-surface-sunken">
      {/* Desktop sidebar: a fixed rail, so content never sits underneath it. */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-edge bg-surface-raised lg:flex">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col border-r border-edge bg-surface-raised shadow-raised">
            {sidebar}
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-edge bg-surface-raised/85 px-4 backdrop-blur sm:px-6">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-2 text-content-muted hover:bg-surface-sunken lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={18} />
          </button>

          <Link to="/" className="text-sm font-semibold tracking-tight text-content lg:hidden">
            WOEnv
          </Link>

          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={toggle}
              className="rounded-md p-2 text-content-muted transition-colors hover:bg-surface-sunken hover:text-content"
              title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              aria-label="Toggle colour theme"
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-[1600px] animate-fade-in p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
