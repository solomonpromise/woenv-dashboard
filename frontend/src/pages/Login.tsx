import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import {
  AlertCircle,
  ArrowLeft,
  Gauge,
  Loader2,
  LogIn,
  Moon,
  ShieldCheck,
  Sun,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'
import { authApi, errorMessage } from '../services/api'

interface LoginForm {
  username: string
  password: string
}

/** Talking points on the brand panel, kept to what the app actually does. */
const POINTS = [
  {
    icon: Gauge,
    title: 'Envelope status at a glance',
    body: 'Erosional headroom and critical-flow margin for every well in the fleet.',
  },
  {
    icon: ShieldCheck,
    title: 'Your workbook stays the source',
    body: 'Prosper-computed limits are used as given, never silently recalculated.',
  },
] as const

export default function Login() {
  const navigate = useNavigate()
  const { setSession, setUser } = useAuthStore()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const { theme, toggle } = useThemeStore()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>()

  const onSubmit = async (form: LoginForm) => {
    setError(null)
    try {
      const { data } = await authApi.login(form.username, form.password)
      setSession(data.access_token)

      // Fetch the real identity rather than assuming a role, so the UI can gate
      // admin-only actions correctly from the first render.
      try {
        const me = await authApi.me()
        setUser(me.data)
      } catch {
        // A missing /auth/me should not block sign-in; Layout retries.
      }

      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Sign in failed'))
    }
  }

  // Reaching /login with a live session - via the landing page or a bookmark -
  // should not present a sign-in form the user does not need.
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return (
    <div className="grid min-h-screen bg-surface-sunken lg:grid-cols-[1.05fr_1fr]">
      {/* ------------------------------------------------------------------ */}
      {/* Brand panel. Hidden on small screens, where it would push the form  */}
      {/* below the fold for no benefit.                                      */}
      {/* ------------------------------------------------------------------ */}
      <aside className="aurora grid-lines relative hidden overflow-hidden bg-surface-raised lg:flex lg:flex-col lg:justify-between lg:p-12">
        <Link
          to="/"
          className="relative z-10 inline-flex items-center gap-3 self-start"
          title="Back to the landing page"
        >
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary-600 text-base font-bold text-white shadow-btn-primary">
            W
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-content">WOEnv</p>
            <p className="text-2xs text-content-subtle">Operating Envelopes</p>
          </div>
        </Link>

        <div className="relative z-10 max-w-md animate-rise-in">
          <h2 className="text-[2rem] font-semibold leading-[1.2] tracking-tight text-content">
            Every well has a window it has to produce inside.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-content-muted">
            WOEnv reads your field workbooks and shows you, well by well, where that
            window sits and which wells have left it.
          </p>

          <div className="mt-9 space-y-5">
            {POINTS.map(({ icon: Icon, title, body }) => (
              <div key={title} className="flex gap-3.5">
                <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-600/10 text-primary-600 ring-1 ring-inset ring-primary-500/20 dark:text-primary-400">
                  <Icon size={17} />
                </div>
                <div>
                  <p className="text-sm font-medium text-content">{title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-content-muted">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-2xs text-content-subtle">
          UGHE · UTOR · UGWest — Proprietary, all rights reserved
        </p>
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* Form panel                                                          */}
      {/* ------------------------------------------------------------------ */}
      <main className="relative flex items-center justify-center px-4 py-10 sm:px-8">
        {/* The small-screen backdrop, since the brand panel is hidden there. */}
        <div aria-hidden className="aurora pointer-events-none absolute inset-0 lg:hidden" />

        <div className="absolute right-4 top-4 flex items-center gap-1 sm:right-6 sm:top-6">
          <Link
            to="/"
            className="btn-ghost text-xs lg:hidden"
            title="Back to the landing page"
          >
            <ArrowLeft size={14} />
            Home
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

        <div className="relative w-full max-w-[25rem] animate-rise-in">
          {/* Small-screen brand mark, doubling as the way back to landing. */}
          <Link to="/" className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary-600 text-base font-bold text-white shadow-btn-primary">
              W
            </div>
            <span className="text-base font-semibold tracking-tight text-content">WOEnv</span>
          </Link>

          <div className="mb-7">
            <h1 className="text-2xl font-semibold tracking-tight text-content">Welcome back</h1>
            <p className="mt-1.5 text-sm text-content-muted">
              Sign in to reach the operating-envelope dashboard.
            </p>
          </div>

          <div className="card card-pad shadow-raised sm:p-7">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-2.5 rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2.5"
                >
                  <AlertCircle size={15} className="mt-0.5 shrink-0 text-breach" />
                  <p className="text-xs text-red-700 dark:text-red-300">{error}</p>
                </div>
              )}

              <div>
                <label className="label" htmlFor="username">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  className="input"
                  placeholder="Enter your username"
                  {...register('username', { required: 'Username is required' })}
                />
                {errors.username && (
                  <p className="mt-1.5 text-xs text-breach">{errors.username.message}</p>
                )}
              </div>

              <div>
                <label className="label" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  className="input"
                  placeholder="Enter your password"
                  {...register('password', { required: 'Password is required' })}
                />
                {errors.password && (
                  <p className="mt-1.5 text-xs text-breach">{errors.password.message}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary w-full py-2.5 text-[0.9375rem]"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    <LogIn size={16} />
                    Sign in
                  </>
                )}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs text-content-subtle">
            Access is granted by an administrator.{' '}
            <Link to="/" className="font-medium text-primary-600 hover:underline dark:text-primary-400">
              Back to home
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}
