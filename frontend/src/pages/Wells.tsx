import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Search, SlidersHorizontal } from 'lucide-react'
import { fieldsApi, wellsApi, type Well } from '../services/api'
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  StatusBadge,
} from '../components/ui'

const STATUSES = ['Flowing', 'Closed-in', 'Suspended', 'Unknown']

type SortKey = 'name' | 'status' | 'well_type'

export default function WellsPage() {
  const [search, setSearch] = useState('')
  const [fieldId, setFieldId] = useState<number | null>(null)
  const [status, setStatus] = useState<string>('')
  const [sort, setSort] = useState<SortKey>('name')

  const fields = useQuery({
    queryKey: ['fields'],
    queryFn: () => fieldsApi.getAll().then((r) => r.data),
  })

  const wells = useQuery({
    queryKey: ['wells', fieldId, status],
    queryFn: () =>
      wellsApi
        .getAll({ field_id: fieldId ?? undefined, status: status || undefined })
        .then((r) => r.data),
  })

  const fieldNames = useMemo(
    () => new Map((fields.data ?? []).map((f) => [f.id, f.code])),
    [fields.data],
  )

  // Search and sort client-side: the full well list is a few hundred rows, so
  // a round trip per keystroke would cost more than it saves.
  const visible = useMemo(() => {
    const term = search.trim().toLowerCase()
    const rows = (wells.data ?? []).filter((well) =>
      term ? well.name.toLowerCase().includes(term) : true,
    )
    return rows.sort((a, b) => {
      const left = String(a[sort] ?? '')
      const right = String(b[sort] ?? '')
      return left.localeCompare(right, undefined, { numeric: true })
    })
  }, [wells.data, search, sort])

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-content">Wells</h1>
        <p className="mt-0.5 text-sm text-content-muted">
          {wells.data ? `${visible.length} of ${wells.data.length} wells` : 'Loading wells…'}
        </p>
      </header>

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-edge p-4">
          <div className="relative min-w-[200px] flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-content-subtle"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by well name…"
              className="input pl-9"
              aria-label="Search wells"
            />
          </div>

          <select
            value={fieldId ?? ''}
            onChange={(e) => setFieldId(e.target.value ? Number(e.target.value) : null)}
            className="input w-auto min-w-[10rem]"
            aria-label="Filter by field"
          >
            <option value="">All fields</option>
            {(fields.data ?? []).map((field) => (
              <option key={field.id} value={field.id}>
                {field.name}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="input w-auto min-w-[9rem]"
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-xs text-content-muted">
            <SlidersHorizontal size={14} />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="input w-auto"
              aria-label="Sort wells"
            >
              <option value="name">Name</option>
              <option value="status">Status</option>
              <option value="well_type">Type</option>
            </select>
          </label>
        </div>

        {wells.isLoading ? (
          <LoadingBlock label="Loading wells…" />
        ) : wells.isError ? (
          <ErrorState onRetry={() => wells.refetch()} />
        ) : !visible.length ? (
          <EmptyState
            title="No wells match"
            description="Try clearing the search box or widening the field and status filters."
          />
        ) : (
          <div className="table-wrap max-h-[70vh]">
            <table className="table">
              <thead>
                <tr>
                  <th>Well</th>
                  <th>Field</th>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Production method</th>
                  <th>Bean model</th>
                  <th aria-label="Open" />
                </tr>
              </thead>
              <tbody>
                {visible.map((well) => (
                  <WellRow key={well.id} well={well} fieldCode={fieldNames.get(well.field_id)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

function WellRow({ well, fieldCode }: { well: Well; fieldCode?: string }) {
  return (
    <tr>
      <td>
        <Link
          to={`/wells/${well.id}`}
          className="font-medium text-content hover:text-primary-600"
        >
          {well.name}
        </Link>
      </td>
      <td className="text-content-muted">{fieldCode ?? '—'}</td>
      <td>
        <StatusBadge status={well.status} />
      </td>
      <td className="text-content-muted">{well.well_type ?? '—'}</td>
      <td className="text-content-muted">{well.prod_method ?? '—'}</td>
      <td className="text-content-muted">{well.bean_model ?? '—'}</td>
      <td className="text-right">
        <Link
          to={`/wells/${well.id}`}
          className="inline-flex text-content-subtle hover:text-primary-600"
          aria-label={`Open ${well.name}`}
        >
          <ChevronRight size={16} />
        </Link>
      </td>
    </tr>
  )
}
