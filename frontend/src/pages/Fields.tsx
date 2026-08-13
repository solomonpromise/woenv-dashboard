import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowUpRight, Droplets, MapPin } from 'lucide-react'
import { statsApi, type FieldStats } from '../services/api'
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  formatCompact,
  formatNumber,
} from '../components/ui'

export default function FieldsPage() {
  const fields = useQuery({
    queryKey: ['fieldStats'],
    queryFn: () => statsApi.fields().then((r) => r.data),
  })

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-content">Fields</h1>
        <p className="mt-0.5 text-sm text-content-muted">
          Well counts and latest-test production for each field
        </p>
      </header>

      {fields.isLoading ? (
        <Card>
          <LoadingBlock label="Loading fields…" />
        </Card>
      ) : fields.isError ? (
        <Card>
          <ErrorState onRetry={() => fields.refetch()} />
        </Card>
      ) : !fields.data?.length ? (
        <Card>
          <EmptyState
            icon={<MapPin className="h-7 w-7" />}
            title="No fields yet"
            description="Upload a WOEnv workbook to create fields and wells."
            action={
              <Link to="/dashboard/upload" className="btn-primary">
                Upload data
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {fields.data.map((field) => (
            <FieldCard key={field.field_id} field={field} />
          ))}
        </div>
      )}
    </div>
  )
}

function FieldCard({ field }: { field: FieldStats }) {
  const empty = field.total_wells === 0
  const flowingShare = field.total_wells ? field.flowing_wells / field.total_wells : 0

  return (
    <Card className="card-pad transition-shadow hover:shadow-raised">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold tracking-tight text-content">
            {field.name}
          </h2>
          <p className="mt-0.5 font-mono text-2xs uppercase tracking-wider text-content-subtle">
            {field.code}
          </p>
        </div>
        <Link
          to={`/dashboard/wells?field=${field.field_id}`}
          className="shrink-0 text-content-subtle transition-colors hover:text-primary-600"
          aria-label={`View wells in ${field.name}`}
        >
          <ArrowUpRight size={16} />
        </Link>
      </div>

      {empty ? (
        <p className="mt-6 text-xs text-content-subtle">
          No wells loaded for this field yet.
        </p>
      ) : (
        <>
          <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3">
            <Metric
              icon={<Activity size={13} />}
              label="Wells"
              value={formatNumber(field.total_wells)}
            />
            <Metric
              icon={<Droplets size={13} />}
              label="Oil"
              value={`${formatCompact(field.oil_rate_stbd)} stb/d`}
            />
            <Metric label="Gross" value={`${formatCompact(field.gross_rate_stbd)} stb/d`} />
            <Metric
              label="Avg BSW"
              value={
                field.avg_bsw_percent != null
                  ? `${formatNumber(field.avg_bsw_percent, { decimals: 1 })}%`
                  : '—'
              }
            />
          </dl>

          <div className="mt-5">
            <div className="mb-1.5 flex items-center justify-between text-2xs text-content-subtle">
              <span>{field.flowing_wells} flowing</span>
              <span>{field.closed_wells} closed-in</span>
            </div>
            <div
              className="h-1.5 overflow-hidden rounded-full bg-edge"
              role="img"
              aria-label={`${field.flowing_wells} of ${field.total_wells} wells flowing`}
            >
              <div
                className="h-full rounded-full bg-emerald-500 transition-all"
                style={{ width: `${Math.round(flowingShare * 100)}%` }}
              />
            </div>
          </div>
        </>
      )}
    </Card>
  )
}

function Metric({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div>
      <dt className="flex items-center gap-1.5 text-2xs uppercase tracking-wide text-content-subtle">
        {icon}
        {label}
      </dt>
      <dd className="numeric mt-0.5 text-sm font-semibold text-content">{value}</dd>
    </div>
  )
}
