import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, Info } from 'lucide-react'
import { envelopesApi, wellsApi } from '../services/api'
import OperatingEnvelopeChart from '../components/charts/OperatingEnvelopeChart'
import BSWTrendChart from '../components/charts/BSWTrendChart'
import GORGLRTrendChart from '../components/charts/GORGLRTrendChart'
import ProductionTrendChart from '../components/charts/ProductionTrendChart'
import {
  Badge,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  LoadingBlock,
  StatusBadge,
  formatDate,
  formatNumber,
} from '../components/ui'

export default function WellDetailPage() {
  const { wellId } = useParams<{ wellId: string }>()
  const id = Number(wellId)

  const well = useQuery({
    queryKey: ['well', id],
    queryFn: () => wellsApi.getById(id).then((r) => r.data),
    enabled: Number.isFinite(id),
  })

  const envelope = useQuery({
    queryKey: ['envelope', id],
    queryFn: () => envelopesApi.getByWellId(id).then((r) => r.data),
    enabled: Number.isFinite(id),
  })

  const history = useQuery({
    queryKey: ['history', id],
    queryFn: () => wellsApi.getHistory(id, 50).then((r) => r.data),
    enabled: Number.isFinite(id),
  })

  if (!Number.isFinite(id)) {
    return (
      <Card>
        <EmptyState title="Invalid well" description="That well id is not a number." />
      </Card>
    )
  }

  if (well.isLoading) return <LoadingBlock height="h-96" label="Loading well…" />
  if (well.isError) {
    return (
      <Card>
        <ErrorState
          title="Well not found"
          description="This well may have been removed."
          onRetry={() => well.refetch()}
        />
      </Card>
    )
  }

  const env = envelope.data
  const test = env?.latest_test
  const breached = env?.within_erosional_limit === false

  return (
    <div className="space-y-5">
      <div>
        <Link
          to="/dashboard/wells"
          className="inline-flex items-center gap-1.5 text-xs text-content-muted hover:text-content"
        >
          <ArrowLeft size={14} />
          All wells
        </Link>

        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight text-content">{well.data?.name}</h1>
          <StatusBadge status={well.data?.status} />
          {well.data?.well_type && <Badge>{well.data.well_type}</Badge>}
          {well.data?.prod_method && <Badge tone="info">{well.data.prod_method}</Badge>}
          {breached && (
            <Badge tone="danger">
              <AlertTriangle size={10} />
              Outside envelope
            </Badge>
          )}
        </div>
      </div>

      {/* Anything the backend could not do exactly is stated, not hidden. */}
      {env?.warnings?.length ? (
        <div className="card border-l-2 border-l-amber-500 card-pad">
          <div className="flex gap-3">
            <Info size={16} className="mt-0.5 shrink-0 text-amber-500" />
            <ul className="space-y-1 text-xs text-content-muted">
              {env.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
        <Stat label="Latest test" value={formatDate(test?.date)} />
        <Stat label="FTHP" value={formatNumber(test?.fthp)} unit="psig" />
        <Stat label="Gross rate" value={formatNumber(test?.gross_rate)} unit="stb/d" />
        <Stat label="Oil rate" value={formatNumber(test?.oil_rate)} unit="stb/d" />
        <Stat
          label="BSW"
          value={test?.bsw_percent != null ? formatNumber(test.bsw_percent, { decimals: 1 }) : '—'}
          unit="%"
        />
        <Stat
          label="Erosional limit"
          value={formatNumber(env?.erosional_rate_limit)}
          unit="stb/d"
          tone={breached ? 'danger' : undefined}
          hint={env?.erosional_limit_source === 'workbook' ? 'from workbook' : env?.erosional_limit_source}
        />
      </div>

      <Card>
        <CardHeader
          title="Operating envelope"
          subtitle={
            env?.thp_curve_source === 'workbook'
              ? 'THP curve as computed in the field workbook'
              : env?.thp_curve_source?.startsWith('model')
              ? `THP curve modelled with the ${env.thp_curve_source.split(':')[1]} bean correlation`
              : undefined
          }
          actions={
            env?.bean_model ? <Badge tone="info">Bean: {env.bean_model}</Badge> : undefined
          }
        />
        <div className="p-4">
          {envelope.isLoading ? (
            <LoadingBlock height="h-80" />
          ) : envelope.isError ? (
            <ErrorState height="h-80" onRetry={() => envelope.refetch()} />
          ) : (
            <OperatingEnvelopeChart data={env} />
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader title="Production trend" subtitle="Oil and water rates with FTHP" />
          <div className="p-4">
            {history.isLoading ? (
              <LoadingBlock height="h-72" />
            ) : (
              <ProductionTrendChart data={history.data} />
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Water cut" subtitle="BSW over the test history" />
          <div className="p-4">
            {history.isLoading ? <LoadingBlock height="h-72" /> : <BSWTrendChart data={history.data} />}
          </div>
        </Card>

        <Card>
          <CardHeader title="Gas ratios" subtitle="GOR per barrel of oil, GLR per barrel of liquid" />
          <div className="p-4">
            {history.isLoading ? (
              <LoadingBlock height="h-72" />
            ) : (
              <GORGLRTrendChart data={history.data} />
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Test history"
            subtitle={
              history.data
                ? `${history.data.length} test${history.data.length === 1 ? '' : 's'}`
                : undefined
            }
          />
          {history.isLoading ? (
            <LoadingBlock height="h-72" />
          ) : history.isError ? (
            <ErrorState height="h-72" onRetry={() => history.refetch()} />
          ) : !history.data?.length ? (
            <EmptyState height="h-72" title="No tests recorded" />
          ) : (
            <div className="table-wrap max-h-72">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th className="text-right">FTHP</th>
                    <th className="text-right">Choke</th>
                    <th className="text-right">Gross</th>
                    <th className="text-right">Oil</th>
                    <th className="text-right">BSW</th>
                  </tr>
                </thead>
                <tbody>
                  {history.data.map((row) => (
                    <tr key={row.id}>
                      <td>{formatDate(row.test_start)}</td>
                      <td className="numeric text-right">{formatNumber(row.fthp_psig)}</td>
                      <td className="numeric text-right">{formatNumber(row.choke_size)}</td>
                      <td className="numeric text-right">{formatNumber(row.gross_rate_stbd)}</td>
                      <td className="numeric text-right">{formatNumber(row.oil_rate_stbd)}</td>
                      <td className="numeric text-right">
                        {row.bsw_percent != null
                          ? `${formatNumber(row.bsw_percent, { decimals: 1 })}%`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

function Stat({
  label,
  value,
  unit,
  hint,
  tone,
}: {
  label: string
  value: string
  unit?: string
  hint?: string
  tone?: 'danger'
}) {
  return (
    <div className="card card-pad">
      <p className="text-2xs font-medium uppercase tracking-wide text-content-subtle">{label}</p>
      <p
        className={`numeric mt-1 flex items-baseline gap-1 text-lg font-semibold ${
          tone === 'danger' ? 'text-breach' : 'text-content'
        }`}
      >
        {value}
        {unit && value !== '—' && (
          <span className="text-2xs font-medium text-content-subtle">{unit}</span>
        )}
      </p>
      {hint && <p className="mt-0.5 text-2xs text-content-subtle">{hint}</p>}
    </div>
  )
}
