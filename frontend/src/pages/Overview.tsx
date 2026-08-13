import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CircleDot,
  Droplets,
  Flame,
  Gauge,
  Waves,
} from 'lucide-react'
import { fieldsApi, statsApi, type EnvelopeAlert } from '../services/api'
import KPICard from '../components/dashboard/KPICard'
import {
  Badge,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  LoadingBlock,
  formatCompact,
  formatDate,
  formatNumber,
} from '../components/ui'

const ALERT_LABELS: Record<string, string> = {
  above_erosional_limit: 'Above erosional limit',
  sub_critical_flow: 'Sub-critical flow',
}

export default function Overview() {
  const [fieldId, setFieldId] = useState<number | null>(null)

  const fields = useQuery({
    queryKey: ['fields'],
    queryFn: () => fieldsApi.getAll().then((r) => r.data),
  })

  const overview = useQuery({
    queryKey: ['overview', fieldId],
    queryFn: () => statsApi.overview(fieldId ?? undefined).then((r) => r.data),
  })

  const breakdown = useQuery({
    queryKey: ['fieldStats'],
    queryFn: () => statsApi.fields().then((r) => r.data),
  })

  const alerts = useQuery({
    queryKey: ['alerts', fieldId],
    queryFn: () => statsApi.alerts(fieldId ?? undefined).then((r) => r.data),
  })

  const stats = overview.data

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-content">Overview</h1>
          <p className="mt-0.5 text-sm text-content-muted">
            Fleet-wide production and operating-envelope status
          </p>
        </div>

        <label className="flex items-center gap-2">
          <span className="text-xs font-medium text-content-muted">Field</span>
          <select
            value={fieldId ?? ''}
            onChange={(e) => setFieldId(e.target.value ? Number(e.target.value) : null)}
            className="input w-48"
          >
            <option value="">All fields</option>
            {(fields.data ?? []).map((field) => (
              <option key={field.id} value={field.id}>
                {field.name}
              </option>
            ))}
          </select>
        </label>
      </header>

      {overview.isError ? (
        <Card>
          <ErrorState
            description="Could not load the overview statistics."
            onRetry={() => overview.refetch()}
          />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KPICard
              title="Wells"
              value={formatNumber(stats?.total_wells)}
              icon={<Activity size={18} />}
              tone="primary"
              loading={overview.isLoading}
              hint={
                stats
                  ? `${stats.flowing_wells} flowing · ${stats.closed_wells} closed-in`
                  : undefined
              }
            />
            <KPICard
              title="Oil rate"
              value={formatCompact(stats?.oil_rate_stbd)}
              unit="stb/d"
              icon={<Droplets size={18} />}
              tone="success"
              loading={overview.isLoading}
              hint={stats ? `${formatCompact(stats.gross_rate_stbd)} stb/d gross` : undefined}
            />
            <KPICard
              title="Water rate"
              value={formatCompact(stats?.water_rate_stbd)}
              unit="stb/d"
              icon={<Waves size={18} />}
              tone="water"
              loading={overview.isLoading}
              hint={
                stats?.avg_bsw_percent != null
                  ? `${formatNumber(stats.avg_bsw_percent, { decimals: 1 })}% average BSW`
                  : undefined
              }
            />
            <KPICard
              title="Gas rate"
              value={formatCompact(stats?.gas_rate_mscfd)}
              unit="Mscf/d"
              icon={<Flame size={18} />}
              tone="gas"
              loading={overview.isLoading}
              hint={stats ? `From ${stats.tested_wells} tested wells` : undefined}
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
            <Card className="xl:col-span-3">
              <CardHeader
                title="Fields"
                subtitle="Production summed over each well's most recent test"
                actions={
                  <Link to="/dashboard/fields" className="btn-ghost text-xs">
                    View all <ArrowUpRight size={14} />
                  </Link>
                }
              />
              {breakdown.isLoading ? (
                <LoadingBlock height="h-56" />
              ) : breakdown.isError ? (
                <ErrorState height="h-56" onRetry={() => breakdown.refetch()} />
              ) : (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Field</th>
                        <th className="text-right">Wells</th>
                        <th className="text-right">Flowing</th>
                        <th className="text-right">Oil (stb/d)</th>
                        <th className="text-right">BSW</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(breakdown.data ?? []).map((field) => (
                        <tr key={field.field_id}>
                          <td>
                            <button
                              onClick={() => setFieldId(field.field_id)}
                              className="font-medium text-content hover:text-primary-600"
                            >
                              {field.name}
                            </button>
                            <span className="ml-2 text-2xs text-content-subtle">{field.code}</span>
                          </td>
                          <td className="numeric text-right">{field.total_wells}</td>
                          <td className="numeric text-right text-emerald-600 dark:text-emerald-400">
                            {field.flowing_wells}
                          </td>
                          <td className="numeric text-right">
                            {formatNumber(field.oil_rate_stbd)}
                          </td>
                          <td className="numeric text-right">
                            {field.avg_bsw_percent != null
                              ? `${formatNumber(field.avg_bsw_percent, { decimals: 1 })}%`
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card className="xl:col-span-2">
              <CardHeader
                title="Envelope alerts"
                subtitle="Wells whose latest test breaches a bound"
                actions={
                  alerts.data?.length ? (
                    <Badge tone="danger">{alerts.data.length}</Badge>
                  ) : undefined
                }
              />
              {alerts.isLoading ? (
                <LoadingBlock height="h-56" />
              ) : alerts.isError ? (
                <ErrorState height="h-56" onRetry={() => alerts.refetch()} />
              ) : !alerts.data?.length ? (
                <EmptyState
                  height="h-56"
                  icon={<CircleDot className="h-7 w-7 text-emerald-500" />}
                  title="All wells within envelope"
                  description="No well is producing above its erosional limit or flowing sub-critically."
                />
              ) : (
                <ul className="max-h-[22rem] divide-y divide-edge/60 overflow-y-auto">
                  {alerts.data.map((alert) => (
                    <AlertRow key={alert.well_id} alert={alert} />
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

function AlertRow({ alert }: { alert: EnvelopeAlert }) {
  const over = alert.reasons.includes('above_erosional_limit')

  return (
    <li className="px-5 py-3 transition-colors hover:bg-surface-sunken/60">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            to={`/dashboard/wells/${alert.well_id}`}
            className="text-sm font-medium text-content hover:text-primary-600"
          >
            {alert.well_name}
          </Link>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {alert.reasons.map((reason) => (
              <Badge key={reason} tone={reason === 'above_erosional_limit' ? 'danger' : 'warning'}>
                <AlertTriangle size={10} />
                {ALERT_LABELS[reason] ?? reason}
              </Badge>
            ))}
          </div>
          <p className="mt-1.5 text-2xs text-content-subtle">
            Tested {formatDate(alert.test_start)}
          </p>
        </div>

        <div className="shrink-0 text-right">
          {over && alert.utilisation != null ? (
            <>
              <p className="numeric text-sm font-semibold text-breach">
                {formatNumber(alert.utilisation * 100)}%
              </p>
              <p className="text-2xs text-content-subtle">of limit</p>
              <p className="numeric mt-1 text-2xs text-content-subtle">
                {formatNumber(alert.gross_rate_stbd)} / {formatNumber(alert.erosional_limit)}
              </p>
            </>
          ) : (
            <>
              <p className="numeric flex items-center gap-1 text-sm font-semibold text-amber-600 dark:text-amber-400">
                <Gauge size={13} />
                {formatNumber(alert.fthp_psig)}
              </p>
              <p className="text-2xs text-content-subtle">psig FTHP</p>
              <p className="numeric mt-1 text-2xs text-content-subtle">
                need {formatNumber((alert.sep_pressure ?? 0) * 1.7)}
              </p>
            </>
          )}
        </div>
      </div>
    </li>
  )
}
