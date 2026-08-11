import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
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

/** Oil and water rates stacked to gross, with FTHP on a secondary axis. */
export default function ProductionTrendChart({ data, height = 300 }: Props) {
  const theme = useChartTheme()

  const series = (data ?? [])
    .map((test) => ({
      date: test.test_start,
      oil: test.oil_rate_stbd,
      water: test.water_rate_stbd,
      fthp: test.fthp_psig,
    }))
    .filter((row) => row.oil != null || row.water != null)
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  if (!series.length) {
    return (
      <EmptyState
        height={`h-[${height}px]`}
        title="No production data"
        description="No test in the selected history reported oil or water rates."
      />
    )
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={series} margin={{ top: 12, right: 12, bottom: 8, left: 4 }}>
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
            yAxisId="rate"
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            width={56}
            tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value))}
            label={{
              value: 'stb/d',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: theme.text, textAnchor: 'middle' },
            }}
          />
          <YAxis
            yAxisId="pressure"
            orientation="right"
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            width={52}
            label={{
              value: 'psig',
              angle: 90,
              position: 'insideRight',
              style: { fontSize: 11, fill: theme.text, textAnchor: 'middle' },
            }}
          />
          <Tooltip
            {...tooltipStyles(theme)}
            formatter={(value: number, name: string) => [
              formatNumber(value, { unit: name === 'FTHP' ? 'psig' : 'stb/d' }),
              name,
            ]}
            labelFormatter={(label) => formatDate(String(label))}
          />
          <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 11, color: theme.text }} />

          <Area
            yAxisId="rate"
            type="monotone"
            dataKey="oil"
            name="Oil"
            stackId="liquid"
            stroke={SERIES_COLORS.oil}
            fill={SERIES_COLORS.oil}
            fillOpacity={0.22}
            strokeWidth={2}
            isAnimationActive={false}
          />
          <Area
            yAxisId="rate"
            type="monotone"
            dataKey="water"
            name="Water"
            stackId="liquid"
            stroke={SERIES_COLORS.water}
            fill={SERIES_COLORS.water}
            fillOpacity={0.22}
            strokeWidth={2}
            isAnimationActive={false}
          />
          <Line
            yAxisId="pressure"
            type="monotone"
            dataKey="fthp"
            name="FTHP"
            stroke={SERIES_COLORS.thp}
            strokeWidth={1.75}
            strokeDasharray="5 3"
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
