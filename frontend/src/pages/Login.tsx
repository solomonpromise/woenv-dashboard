import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { AlertCircle, Loader2, LogIn } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { authApi, errorMessage } from '../services/api'

interface LoginForm {
  username: string
  password: string
}

export default function Login() {
  const navigate = useNavigate()
  const { setSession, setUser } = useAuthStore()
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

      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Sign in failed'))
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-surface-sunken px-4 py-10">
      {/* Soft field-diagram backdrop, purely decorative. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35] dark:opacity-20"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 15%, rgb(37 99 235 / 0.16), transparent 45%),' +
            'radial-gradient(circle at 85% 80%, rgb(16 185 129 / 0.14), transparent 45%)',
        }}
      />

      <div className="relative w-full max-w-sm">
        <div className="mb-7 text-center">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-primary-600 text-lg font-bold text-white shadow-raised">
            W
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-content">WOEnv Dashboard</h1>
          <p className="mt-1 text-sm text-content-muted">Well Operating Envelope Management</p>
        </div>

        <div className="card card-pad">
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

            <button type="submit" disabled={isSubmitting} className="btn-primary w-full py-2.5">
              {isSubmitting ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  <LogIn size={15} />
                  Sign in
                </>
              )}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-2xs text-content-subtle">
          Well Operating Envelope Dashboard
        </p>
      </div>
    </div>
  )
}
