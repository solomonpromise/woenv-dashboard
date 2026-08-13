import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  ChevronsLeft,
  ChevronsRight,
  Home,
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
import { useUIStore } from '../stores/uiStore'
import { authApi } from '../services/api'
import { Badge, cn } from './ui'

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard, end: true },
  { name: 'Fields', href: '/dashboard/fields', icon: MapPin },
  { name: 'Wells', href: '/dashboard/wells', icon: Activity },
  { name: 'Upload Data', href: '/dashboard/upload', icon: Upload },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, setUser, logout } = useAuthStore()
  const { theme, toggle } = useThemeStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
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

  const displayName = user?.full_name || user?.username || 'Signed in'

  /**
   * `collapsed` is passed in rather than read from the store, because the
   * mobile drawer always renders the full sidebar - collapsing is a desktop
   * affordance and there is no rail to collapse to on a drawer.
   */
  const renderSidebar = (collapsed: boolean) => (
    <>
      <div
        className={cn(
          'flex h-16 items-center border-b border-edge',
          collapsed ? 'justify-center px-2' : 'gap-2.5 px-5',
        )}
      >
        {/* The brand doubles as the way back out to the public landing page.
            Collapsed, the rail is too narrow for both it and the toggle, so
            the toggle wins - the top bar's Home control still reaches the
            landing page. */}
        {!collapsed && (
          <Link
            to="/"
            className="flex min-w-0 items-center gap-2.5"
            title="Back to landing page"
          >
            <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 text-sm font-bold text-white shadow-btn-primary">
              W
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight text-content">WOEnv</p>
              <p className="truncate text-2xs text-content-subtle">Operating Envelopes</p>
            </div>
          </Link>
        )}

        {/* Desktop collapse toggle. */}
        <button
          type="button"
          onClick={toggleSidebar}
          className={cn(
            'hidden shrink-0 rounded-md p-2 text-content-muted transition-colors hover:bg-surface-sunken hover:text-content lg:block',
            !collapsed && 'ml-auto',
          )}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
        </button>

        {!collapsed && (
          <button
            onClick={() => setMobileOpen(false)}
            className="ml-auto rounded-md p-1.5 text-content-muted hover:bg-surface-sunken lg:hidden"
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <nav className={cn('flex-1 space-y-1', collapsed ? 'p-2' : 'p-3')}>
        {navigation.map(({ name, href, icon: Icon, end }) => (
          <NavLink
            key={name}
            to={href}
            end={end}
            // The label is the only accessible name when collapsed, so it is
            // kept in the DOM and hidden visually rather than removed.
            title={collapsed ? name : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center rounded-lg text-sm font-medium transition-colors',
                collapsed ? 'justify-center px-0 py-2.5' : 'gap-3 px-3 py-2',
                isActive
                  ? 'bg-primary-600/10 text-primary-700 dark:text-primary-300'
                  : 'text-content-muted hover:bg-surface-sunken hover:text-content',
              )
            }
          >
            <Icon className="shrink-0" size={18} />
            <span className={collapsed ? 'sr-only' : undefined}>{name}</span>
          </NavLink>
        ))}
      </nav>

      <div className={cn('border-t border-edge', collapsed ? 'p-2' : 'p-3')}>
        <div
          className={cn(
            'flex items-center rounded-lg',
            collapsed ? 'flex-col gap-1 px-0 py-1' : 'gap-3 px-2 py-2',
          )}
        >
          <div
            className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-surface-sunken text-2xs font-semibold text-content-muted ring-1 ring-edge"
            title={collapsed ? `${displayName}${user?.role ? ` · ${user.role}` : ''}` : undefined}
          >
            {initials}
          </div>

          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-content">{displayName}</p>
              {user?.role && (
                <Badge tone={user.role === 'admin' ? 'info' : 'neutral'} className="mt-1">
                  {user.role}
                </Badge>
              )}
            </div>
          )}

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
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-edge bg-surface-raised transition-[width] duration-200 ease-out lg:flex',
          sidebarCollapsed ? 'w-[4.5rem]' : 'w-64',
        )}
      >
        {renderSidebar(sidebarCollapsed)}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col border-r border-edge bg-surface-raised shadow-raised">
            {renderSidebar(false)}
          </aside>
        </div>
      )}

      <div
        className={cn(
          'transition-[padding] duration-200 ease-out',
          sidebarCollapsed ? 'lg:pl-[4.5rem]' : 'lg:pl-64',
        )}
      >
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-edge bg-surface-raised/85 px-4 backdrop-blur sm:px-6">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-2 text-content-muted hover:bg-surface-sunken lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={18} />
          </button>

          <Link
            to="/dashboard"
            className="text-sm font-semibold tracking-tight text-content lg:hidden"
          >
            WOEnv
          </Link>

          <div className="ml-auto flex items-center gap-1">
            <Link
              to="/"
              className="rounded-md p-2 text-content-muted transition-colors hover:bg-surface-sunken hover:text-content"
              title="Landing page"
              aria-label="Go to the landing page"
            >
              <Home size={18} />
            </Link>

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
