import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload as UploadIcon,
  X,
} from 'lucide-react'
import { errorMessage, uploadApi, type UploadResult } from '../services/api'
import { Card, CardHeader, cn, formatNumber } from '../components/ui'

const ACCEPTED = /\.(xlsx|xlsm|xls)$/i
const MAX_BYTES = 50 * 1024 * 1024

export default function UploadPage() {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  const selectFile = useCallback((candidate: File) => {
    setResult(null)
    if (!ACCEPTED.test(candidate.name)) {
      setError('Please select an Excel workbook (.xlsx, .xlsm or .xls).')
      setFile(null)
      return
    }
    if (candidate.size > MAX_BYTES) {
      setError('That file is larger than the 50 MB upload limit.')
      setFile(null)
      return
    }
    setError(null)
    setFile(candidate)
  }, [])

  const reset = () => {
    setFile(null)
    setResult(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const upload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const { data } = await uploadApi.uploadExcel(file)
      setResult(data)
      // Every view derives from this data, so drop the whole cache.
      queryClient.invalidateQueries()
    } catch (err) {
      setError(errorMessage(err, 'Upload failed. Please try again.'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-content">Upload data</h1>
        <p className="mt-0.5 text-sm text-content-muted">
          Import a WOEnv field workbook. Re-uploading the same workbook is safe — existing tests are
          skipped rather than duplicated.
        </p>
      </header>

      <div
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const dropped = e.dataTransfer.files[0]
          if (dropped) selectFile(dropped)
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        role="button"
        tabIndex={0}
        aria-label="Choose a workbook to upload"
        className={cn(
          'card flex cursor-pointer flex-col items-center justify-center border-2 border-dashed px-6 py-12 text-center transition-colors',
          dragging
            ? 'border-primary-500 bg-primary-500/5'
            : file
            ? 'border-emerald-500/50 bg-emerald-500/5'
            : 'border-edge-strong hover:border-primary-400 hover:bg-surface-sunken/60',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xlsm,.xls"
          className="hidden"
          onChange={(e) => {
            const chosen = e.target.files?.[0]
            if (chosen) selectFile(chosen)
          }}
        />

        {file ? (
          <>
            <FileSpreadsheet className="mb-3 h-9 w-9 text-emerald-500" />
            <p className="text-sm font-medium text-content">{file.name}</p>
            <p className="mt-1 text-xs text-content-subtle">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation()
                reset()
              }}
              className="btn-ghost mt-3 text-xs text-breach hover:bg-red-500/10"
            >
              <X size={13} />
              Remove
            </button>
          </>
        ) : (
          <>
            <UploadIcon className="mb-3 h-9 w-9 text-content-subtle" />
            <p className="text-sm font-medium text-content">Drop a workbook here</p>
            <p className="mt-1 text-xs text-content-subtle">or click to browse — .xlsx up to 50 MB</p>
          </>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="card border-l-2 border-l-breach card-pad flex items-start gap-3"
        >
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-breach" />
          <div>
            <p className="text-sm font-medium text-content">Upload failed</p>
            <p className="mt-0.5 text-xs text-content-muted">{error}</p>
          </div>
        </div>
      )}

      {file && !result && (
        <button onClick={upload} disabled={uploading} className="btn-primary w-full py-2.5">
          {uploading ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              Processing workbook…
            </>
          ) : (
            <>
              <UploadIcon size={15} />
              Upload and process
            </>
          )}
        </button>
      )}

      {result && <ResultPanel result={result} onReset={reset} />}

      <Card>
        <CardHeader title="What gets imported" />
        <div className="card-pad pt-3 text-xs leading-relaxed text-content-muted">
          <ul className="space-y-1.5">
            <li>
              <span className="font-medium text-content">Historical Data</span> — well test records:
              rates, FTHP, choke, BSW and gas ratios.
            </li>
            <li>
              <span className="font-medium text-content">Erosional Rates</span> — per-well erosional
              limits and reservoir fluid properties.
            </li>
            <li>
              <span className="font-medium text-content">Envelope Data</span> — the pre-computed THP
              curve, flowline pressure and critical-flow limit.
            </li>
          </ul>
          <p className="mt-3 text-content-subtle">
            Supported fields: UGHE, UTOR and UGWest. The field is detected from the workbook, so
            no manual selection is needed. Workbooks for other fields are rejected.
          </p>
        </div>
      </Card>
    </div>
  )
}

function ResultPanel({ result, onReset }: { result: UploadResult; onReset: () => void }) {
  const clean = result.status === 'success'

  const metrics = [
    { label: 'Wells created', value: result.wells_created },
    { label: 'Wells updated', value: result.wells_updated },
    { label: 'Tests added', value: result.tests_created },
    { label: 'Duplicates skipped', value: result.tests_skipped },
    { label: 'Erosional records', value: result.erosionals_created },
    { label: 'Envelope points', value: result.envelope_points },
  ]

  return (
    <div className="space-y-4">
      <Card className={cn('border-l-2', clean ? 'border-l-emerald-500' : 'border-l-amber-500')}>
        <div className="card-pad">
          <div className="flex items-start gap-3">
            {clean ? (
              <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-500" />
            ) : (
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-500" />
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium text-content">
                {clean ? 'Import complete' : 'Imported with warnings'}
              </p>
              <p className="mt-0.5 truncate text-xs text-content-subtle">
                {result.filename} · field {result.field_code}
              </p>
            </div>
          </div>

          <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {metrics.map((metric) => (
              <div key={metric.label}>
                <dt className="text-2xs uppercase tracking-wide text-content-subtle">
                  {metric.label}
                </dt>
                <dd className="numeric mt-0.5 text-lg font-semibold text-content">
                  {formatNumber(metric.value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </Card>

      {result.errors.length > 0 && (
        <Card>
          <CardHeader title={`Warnings (${result.errors.length})`} />
          <ul className="max-h-40 overflow-y-auto px-5 py-3">
            {result.errors.map((warning, index) => (
              <li key={index} className="py-1 font-mono text-2xs text-content-muted">
                {warning}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        <button onClick={onReset} className="btn-secondary">
          Upload another
        </button>
        <Link to="/" className="btn-primary">
          View dashboard
        </Link>
      </div>
    </div>
  )
}
