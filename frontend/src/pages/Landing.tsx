import { Link } from 'react-router-dom'
import {
  ArrowRight,
  AlertTriangle,
  FileSpreadsheet,
  Gauge,
  LayoutDashboard,
  LogIn,
  Moon,
  ShieldCheck,
  Sun,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'

/*
 * Public entry point. Everything here is static - it renders identically to a
 * signed-out visitor and makes no API calls, so it stays useful while the
 * backend is asleep on a free instance.
 */

const CAPABILITIES = [
  {
    icon: AlertTriangle,
    title: 'Envelope alerts',
    // Each card carries its own accent so the grid reads as four distinct
    // capabilities rather than one block of grey text.
    gradient: 'from-rose-500 to-red-600',
    glow: 'shadow-[0_6px_20px_-8px_rgb(239_68_68_/_0.7)]',
    body:
      'Flags wells producing above their erosional rate limit, and wells that have ' +
      'dropped below critical flow where the choke no longer controls the rate.',
  },
  {
    icon: Gauge,
    title: 'Bean correlations',
    gradient: 'from-primary-500 to-primary-700',
    glow: 'shadow-[0_6px_20px_-8px_rgb(37_99_235_/_0.7)]',
    body:
      'Gilbert, Ros, Baxendell and Achong choke models, each driven by measured ' +
      'GOR. Wells with no model assigned fall back to the best-fitting one.',
  },
  {
    icon: FileSpreadsheet,
    title: 'Workbook ingestion',
    gradient: 'from-emerald-500 to-teal-600',
    glow: 'shadow-[0_6px_20px_-8px_rgb(16_185_129_/_0.7)]',
    body:
      'Reads the Historical Data, Erosional Rates and Envelope Data sheets, ' +
      'reconciles the columns whose names contradict their contents, and ' +
      'deduplicates on well and test date so re-uploading changes nothing.',
  },
  {
    icon: ShieldCheck,
    title: 'Role-based access',
    gradient: 'from-violet-500 to-indigo-600',
    glow: 'shadow-[0_6px_20px_-8px_rgb(139_92_246_/_0.7)]',
    body:
      'Admin, engineer and viewer roles. Uploading a workbook and recomputing an ' +
      'envelope are restricted to the roles allowed to change stored data.',
  },
] as const

/**
 * The operating envelope, drawn rather than described.
 *
 * Two bounds define it: the erosional rate limit on the right, beyond which
 * produced sand and velocity attack the completion, and the critical-flow floor
 * underneath, below which the well is no longer choke-controlled. The region
 * between them is where a well is meant to sit.
 */
function EnvelopeDiagram() {
  return (
    <svg
      viewBox="0 0 560 360"
      className="h-auto w-full"
      role="img"
      aria-label="Operating envelope chart: a safe region bounded by an erosional rate limit on the right and a critical-flow floor below, with wells plotted inside it and two breaching it."
    >
      <defs>
        <linearGradient id="envFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgb(16 185 129)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="rgb(16 185 129)" stopOpacity="0.04" />
        </linearGradient>
        <linearGradient id="envLine" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgb(52 211 153)" />
          <stop offset="100%" stopColor="rgb(13 148 136)" />
        </linearGradient>
        <filter id="curveGlow" x="-20%" y="-40%" width="140%" height="180%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Grid */}
      <g className="stroke-edge" strokeWidth="1">
        {[32, 96, 160, 224, 288].map((y) => (
          <line key={y} x1="64" y1={y} x2="500" y2={y} />
        ))}
        {[64, 173, 282, 391, 500].map((x) => (
          <line key={x} x1={x} y1="32" x2={x} y2="288" />
        ))}
      </g>

      {/* Safe region, under the well's performance curve and above the floor */}
      <path d="M 64 76 C 160 96, 300 170, 430 214 L 430 238 L 64 238 Z" fill="url(#envFill)" />
      <path
        d="M 64 76 C 160 96, 300 170, 430 214"
        stroke="url(#envLine)"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
        filter="url(#curveGlow)"
      />

      {/* Erosional rate limit */}
      <line
        x1="430"
        y1="32"
        x2="430"
        y2="288"
        className="stroke-breach"
        strokeWidth="1.5"
        strokeDasharray="5 4"
      />
      <text x="424" y="26" textAnchor="end" className="fill-breach text-[11px] font-semibold">
        Erosional limit
      </text>

      {/* Critical-flow floor */}
      <line
        x1="64"
        y1="238"
        x2="500"
        y2="238"
        className="stroke-caution"
        strokeWidth="1.5"
        strokeDasharray="5 4"
      />
      <text x="68" y="252" className="fill-caution text-[11px] font-semibold">
        Critical flow · FTHP = 1.7 × flowline pressure
      </text>

      <text x="104" y="206" className="fill-content-muted text-[11px] font-medium">
        Safe operating envelope
      </text>

      {/* Wells inside the envelope */}
      {[
        [150, 150],
        [232, 172],
        [330, 200],
      ].map(([cx, cy]) => (
        <g key={`${cx}`}>
          <circle cx={cx} cy={cy} r="7" className="fill-flowing/20" />
          <circle cx={cx} cy={cy} r="4.5" className="fill-flowing" />
        </g>
      ))}

      {/* Producing beyond the erosional limit - the one that needs attention. */}
      <circle
        cx="466"
        cy="190"
        r="6"
        className="animate-pulse-ring fill-breach/50"
        style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
      />
      <circle cx="466" cy="190" r="7" className="fill-breach/25" />
      <circle cx="466" cy="190" r="5" className="fill-breach" />

      {/* Fallen below critical flow. Kept clear of the label to its left. */}
      <circle cx="370" cy="262" r="7" className="fill-caution/25" />
      <circle cx="370" cy="262" r="5" className="fill-caution" />

      {/* Axes drawn last so they sit above the fill */}
      <g className="stroke-edge-strong" strokeWidth="1.5">
        <line x1="64" y1="28" x2="64" y2="288" />
        <line x1="64" y1="288" x2="506" y2="288" />
      </g>

      <text x="282" y="322" textAnchor="middle" className="fill-content-subtle text-[11px]">
        Gross liquid rate (stb/d)
      </text>
      <text
        x="20"
        y="160"
        textAnchor="middle"
        transform="rotate(-90 20 160)"
        className="fill-content-subtle text-[11px]"
      >
        FTHP (psig)
      </text>
    </svg>
  )
}

export default function Landing() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const { theme, toggle } = useThemeStore()

  // Signed-out visitors are sent to the login screen; the dashboard link is
  // only offered once there is a session behind it, so the primary call to
  // action never lands on a redirect back to /login.
  const primaryHref = isAuthenticated ? '/dashboard' : '/login'

  const primaryCta = (
    <>
      {isAuthenticated ? (
        <>
          <LayoutDashboard size={17} />
          Open dashboard
        </>
      ) : (
        <>
          <LogIn size={17} />
          Sign in
        </>
      )}
      <ArrowRight size={17} className="transition-transform duration-200 group-hover:translate-x-0.5" />
    </>
  )

  return (
    <div className="min-h-screen bg-surface-sunken">
      <header className="sticky top-0 z-30 border-b border-edge bg-surface-raised/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-sm font-bold text-white shadow-btn-primary">
            W
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight text-content">WOEnv</p>
            <p className="truncate text-2xs text-content-subtle">Operating Envelopes</p>
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <button
              onClick={toggle}
              className="rounded-lg p-2 text-content-muted transition-colors hover:bg-surface-sunken hover:text-content"
              title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              aria-label="Toggle colour theme"
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            {isAuthenticated ? (
              <Link to="/dashboard" className="btn-primary">
                <LayoutDashboard size={15} />
                <span className="hidden sm:inline">Dashboard</span>
              </Link>
            ) : (
              <Link to="/login" className="btn-secondary">
                <LogIn size={15} />
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Hero                                                             */}
      {/* ---------------------------------------------------------------- */}
      <section className="aurora grid-lines relative overflow-hidden border-b border-edge bg-surface-raised">
        <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.05fr_1fr] lg:gap-16">
          <div>
            <span
              className="badge animate-rise-in border border-primary-500/25 bg-primary-500/10 text-primary-700 ring-0 dark:text-primary-300"
              style={{ animationDelay: '40ms' }}
            >
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-flowing opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-flowing" />
              </span>
              UGHE · UTOR · UGWest
            </span>

            <h1
              className="text-gradient mt-6 animate-rise-in text-[2.25rem] font-semibold leading-[1.1] tracking-[-0.02em] sm:text-5xl lg:text-[3.25rem]"
              style={{ animationDelay: '90ms' }}
            >
              Every well has a window it has to produce inside.
            </h1>

            <p
              className="mt-6 max-w-xl animate-rise-in text-base leading-relaxed text-content-muted sm:text-[1.0625rem]"
              style={{ animationDelay: '150ms' }}
            >
              Produce too hard and sand and velocity begin eroding the completion. Produce
              too softly and the well drops below critical flow, where the bean no longer
              governs the rate and the test data stops meaning what it says. WOEnv reads
              your field workbooks and shows you, well by well, exactly where that window
              sits and which wells have left it.
            </p>

            <div
              className="mt-9 flex animate-rise-in flex-wrap items-center gap-3"
              style={{ animationDelay: '210ms' }}
            >
              <Link to={primaryHref} className="btn-primary group px-6 py-3 text-[0.9375rem]">
                {primaryCta}
              </Link>

              <a href="#what-it-does" className="btn-secondary px-6 py-3 text-[0.9375rem]">
                What it does
              </a>
            </div>

            {isAuthenticated && (
              <p className="mt-5 text-xs text-content-subtle">
                Signed in as {user?.full_name || user?.username || 'your account'}.
              </p>
            )}
          </div>

          {/* Diagram, lifted off the page with a soft colour bloom behind it. */}
          <div className="relative animate-rise-in" style={{ animationDelay: '260ms' }}>
            <div
              aria-hidden
              className="absolute -inset-6 rounded-[2.5rem] bg-gradient-to-tr from-primary-500/25 via-transparent to-emerald-500/25 blur-3xl"
            />
            <div className="card card-pad relative shadow-floating">
              <EnvelopeDiagram />
              <div className="mt-4 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 border-t border-edge pt-4">
                {[
                  ['bg-flowing', 'Within envelope'],
                  ['bg-breach', 'Erosional breach'],
                  ['bg-caution', 'Sub-critical flow'],
                ].map(([dot, label]) => (
                  <span key={label} className="flex items-center gap-2 text-2xs text-content-muted">
                    <span className={`h-2 w-2 rounded-full ${dot}`} />
                    {label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Capabilities                                                     */}
      {/* ---------------------------------------------------------------- */}
      <section
        id="what-it-does"
        className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16 sm:px-6 sm:py-20"
      >
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-600 dark:text-primary-400">
            From one spreadsheet
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-content sm:text-3xl">
            What it does with a field workbook
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-content-muted sm:text-base">
            Upload the same spreadsheet the asset engineers already maintain. Everything
            here follows from it — no re-keying, no separate data entry step.
          </p>
        </div>

        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {CAPABILITIES.map(({ icon: Icon, title, body, gradient, glow }) => (
            <article key={title} className="card card-interactive card-pad sm:p-6">
              <div
                className={`mb-4 grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br text-white ${gradient} ${glow}`}
              >
                <Icon size={20} />
              </div>
              <h3 className="text-base font-semibold tracking-tight text-content">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-content-muted">{body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Closing call to action                                           */}
      {/* ---------------------------------------------------------------- */}
      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <div className="relative overflow-hidden rounded-2xl shadow-floating">
          {/* Deep gradient panel - the one saturated block on the page. */}
          <div
            aria-hidden
            className="absolute inset-0 bg-gradient-to-br from-primary-600 via-primary-700 to-indigo-800"
          />
          <div
            aria-hidden
            className="absolute inset-0 opacity-60"
            style={{
              backgroundImage:
                'radial-gradient(ellipse 60% 80% at 85% 15%, rgb(16 185 129 / 0.45), transparent 60%),' +
                'radial-gradient(ellipse 50% 70% at 10% 90%, rgb(99 102 241 / 0.5), transparent 60%)',
            }}
          />

          <div className="relative px-6 py-14 text-center sm:px-10 sm:py-16">
            <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              {isAuthenticated ? 'Pick up where you left off' : 'Sign in to continue'}
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-blue-100/90">
              {isAuthenticated
                ? 'Fleet totals, envelope alerts and per-well trends are waiting in the dashboard.'
                : 'WOEnv is an internal application. Access is granted by an administrator, with viewer, engineer and admin roles.'}
            </p>
            <div className="mt-8 flex justify-center">
              <Link
                to={primaryHref}
                className="btn group bg-white px-6 py-3 text-[0.9375rem] text-primary-700 shadow-floating hover:bg-blue-50"
              >
                {primaryCta}
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-edge">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-7 sm:flex-row sm:px-6">
          <p className="text-2xs text-content-subtle">
            WOEnv — Well Operating Envelope Dashboard
          </p>
          <p className="text-2xs text-content-subtle">Proprietary — all rights reserved</p>
        </div>
      </footer>
    </div>
  )
}
