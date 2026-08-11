import { ReactNode } from 'react'
import { twMerge } from 'tailwind-merge'
import clsx, { ClassValue } from 'clsx'
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/* -------------------------------------------------------------------------- */
/* Card                                                                       */
/* -------------------------------------------------------------------------- */

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('card', className)}>{children}</section>
}

export function CardHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="card-header">
      <div className="min-w-0">
        <h2 className="card-title">{title}</h2>
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  )
}

/* -------------------------------------------------------------------------- */
/* Badge                                                                      */
/* -------------------------------------------------------------------------- */

const badgeTones = {
  neutral: 'bg-surface-sunken text-content-muted ring-edge-strong',
  success: 'bg-emerald-500/10 text-emerald-600 ring-emerald-500/30 dark:text-emerald-400',
  warning: 'bg-amber-500/10 text-amber-600 ring-amber-500/30 dark:text-amber-400',
  danger: 'bg-red-500/10 text-red-600 ring-red-500/30 dark:text-red-400',
  info: 'bg-primary-500/10 text-primary-600 ring-primary-500/30 dark:text-primary-400',
} as const

export type BadgeTone = keyof typeof badgeTones

export function Badge({
  tone = 'neutral',
  children,
  className,
}: {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}) {
  return <span className={cn('badge', badgeTones[tone], className)}>{children}</span>
}

/** Maps a well status onto a consistent colour across every view. */
export function StatusBadge({ status }: { status?: string | null }) {
  const tone: BadgeTone =
    status === 'Flowing' ? 'success' : status === 'Closed-in' ? 'neutral' : 'warning'
  return (
    <Badge tone={tone}>
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          status === 'Flowing'
            ? 'bg-emerald-500'
            : status === 'Closed-in'
            ? 'bg-slate-400'
            : 'bg-amber-500',
        )}
      />
      {status || 'Unknown'}
    </Badge>
  )
}

/* -------------------------------------------------------------------------- */
/* State placeholders                                                         */
/* -------------------------------------------------------------------------- */

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-4 w-4 animate-spin', className)} />
}

export function LoadingBlock({ height = 'h-64', label }: { height?: string; label?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2', height)}>
      <Spinner className="h-5 w-5 text-content-subtle" />
      {label && <p className="text-xs text-content-subtle">{label}</p>}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  height = 'h-64',
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  height?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 text-center', height)}>
      <div className="mb-3 text-content-subtle">{icon ?? <Inbox className="h-7 w-7" />}</div>
      <p className="text-sm font-medium text-content">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-xs leading-relaxed text-content-subtle">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  onRetry,
  height = 'h-64',
}: {
  title?: string
  description?: string
  onRetry?: () => void
  height?: string
}) {
  return (
    <EmptyState
      height={height}
      icon={<AlertTriangle className="h-7 w-7 text-breach" />}
      title={title}
      description={description}
      action={
        onRetry && (
          <button onClick={onRetry} className="btn-secondary">
            Try again
          </button>
        )
      }
    />
  )
}

/* -------------------------------------------------------------------------- */
/* Formatting helpers                                                         */
/* -------------------------------------------------------------------------- */

/** Compact number with a unit; renders an em dash for missing values. */
export function formatNumber(
  value: number | null | undefined,
  { decimals = 0, unit = '' }: { decimals?: number; unit?: string } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const formatted = value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
  return unit ? `${formatted} ${unit}` : formatted
}

/** Abbreviates large rates so KPI tiles stay on one line. */
export function formatCompact(value: number | null | undefined, unit = ''): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const abs = Math.abs(value)
  const [scaled, suffix] =
    abs >= 1_000_000 ? [value / 1_000_000, 'M'] : abs >= 10_000 ? [value / 1_000, 'k'] : [value, '']
  const formatted = scaled.toLocaleString(undefined, {
    maximumFractionDigits: suffix || abs < 100 ? 1 : 0,
  })
  return `${formatted}${suffix}${unit ? ` ${unit}` : ''}`
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' })
}
