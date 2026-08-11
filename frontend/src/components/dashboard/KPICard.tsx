import { ReactNode } from 'react'
import { cn } from '../ui'

type Tone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'water' | 'gas'

const tones: Record<Tone, { icon: string; accent: string }> = {
  neutral: { icon: 'bg-slate-500/10 text-slate-600 dark:text-slate-300', accent: 'bg-slate-400' },
  primary: { icon: 'bg-primary-500/10 text-primary-600 dark:text-primary-400', accent: 'bg-primary-500' },
  success: { icon: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400', accent: 'bg-emerald-500' },
  warning: { icon: 'bg-amber-500/10 text-amber-600 dark:text-amber-400', accent: 'bg-amber-500' },
  danger: { icon: 'bg-red-500/10 text-red-600 dark:text-red-400', accent: 'bg-red-500' },
  water: { icon: 'bg-sky-500/10 text-sky-600 dark:text-sky-400', accent: 'bg-sky-500' },
  gas: { icon: 'bg-amber-500/10 text-amber-600 dark:text-amber-400', accent: 'bg-amber-500' },
}

interface KPICardProps {
  title: string
  value: ReactNode
  unit?: string
  icon: ReactNode
  tone?: Tone
  hint?: ReactNode
  loading?: boolean
}

export default function KPICard({
  title,
  value,
  unit,
  icon,
  tone = 'neutral',
  hint,
  loading,
}: KPICardProps) {
  const palette = tones[tone]

  return (
    <article className="card relative overflow-hidden card-pad">
      {/* Thin accent rail, rather than a solid colour block behind the icon. */}
      <span className={cn('absolute inset-y-0 left-0 w-0.5', palette.accent)} aria-hidden />

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-content-muted">{title}</p>

          {loading ? (
            <div className="mt-2 h-7 w-24 skeleton" />
          ) : (
            <p className="numeric mt-1.5 flex items-baseline gap-1 text-2xl font-semibold tracking-tight text-content">
              {value}
              {unit && <span className="text-xs font-medium text-content-subtle">{unit}</span>}
            </p>
          )}

          {hint && !loading && <p className="mt-1 text-xs text-content-subtle">{hint}</p>}
        </div>

        <div className={cn('grid h-10 w-10 shrink-0 place-items-center rounded-lg', palette.icon)}>
          {icon}
        </div>
      </div>
    </article>
  )
}
