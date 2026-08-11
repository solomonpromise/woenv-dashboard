import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TestRecord } from '../../services/api'
import { EmptyState, formatDate, formatNumber } from '../ui'
import { SERIES_COLORS, tooltipStyles, useChartTheme } from './chartTheme'

interface Props {
  data?: TestRecord[] | null
  height?: number
}

/**
 * GOR and GLR over time.
 *
 * These are distinct quantities: GOR is gas per barrel of oil, GLR is gas per
 * barrel of gross liquid. Ingestion previously wrote GOR into both columns, so
 * the two lines were identical by construction.
 */
export default function GORGLRTrendChart({ data, height = 300 }: Props) {
  const theme = useChartTheme()

  const series = (data ?? [])
    .filter((test) => test.fgor_scfstb != null || test.glr_scfstb != null)
    .map((test) => ({
      date: test.test_start,
      gor: test.fgor_scfstb,
      glr: test.glr_scfstb,
    }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  if (!series.length) {
    return (
      <EmptyState
        height={`h-[${height}px]`}
        title="No gas ratio data"
        description="No test in the selected history reported a GOR or GLR measurement."
      />
    )
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 12, right: 20, bottom: 8, left: 4 }}>
          <CartesianGrid stroke={theme.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            minTickGap={28}
            tickFormatter={(value) =>
              new Date(value).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
            }
          />
          <YAxis
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            width={58}
            tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(0)}k` : String(value))}
            label={{
              value: 'scf/stb',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: theme.text, textAnchor: 'middle' },
            }}
          />
          <Tooltip
            {...tooltipStyles(theme)}
            formatter={(value: number, name: string) => [
              formatNumber(value, { unit: 'scf/stb' }),
              name,
            ]}
            labelFormatter={(label) => formatDate(String(label))}
          />
          <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 11, color: theme.text }} />
          <Line
            type="monotone"
            dataKey="gor"
            name="GOR (per stb oil)"
            stroke={SERIES_COLORS.gor}
            strokeWidth={2}
            dot={{ r: 2.5, fill: SERIES_COLORS.gor, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="glr"
            name="GLR (per stb liquid)"
            stroke={SERIES_COLORS.glr}
            strokeWidth={2}
            dot={{ r: 2.5, fill: SERIES_COLORS.glr, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
