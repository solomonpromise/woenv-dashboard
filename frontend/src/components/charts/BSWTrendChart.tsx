import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
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
 * Water cut over time.
 *
 * `bsw_percent` is a true percentage (0-100). It used to be stored as a
 * fraction and rendered against a 0-100 axis, which pinned every well's trend
 * flat against zero.
 */
export default function BSWTrendChart({ data, height = 300 }: Props) {
  const theme = useChartTheme()

  const series = (data ?? [])
    .filter((test) => test.bsw_percent != null)
    .map((test) => ({
      date: test.test_start,
      bsw: test.bsw_percent as number,
    }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  if (!series.length) {
    return (
      <EmptyState
        height={`h-[${height}px]`}
        title="No water-cut data"
        description="No test in the selected history reported a BSW measurement."
      />
    )
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series} margin={{ top: 12, right: 20, bottom: 8, left: 4 }}>
          <defs>
            <linearGradient id="bswFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={SERIES_COLORS.bsw} stopOpacity={0.28} />
              <stop offset="100%" stopColor={SERIES_COLORS.bsw} stopOpacity={0.02} />
            </linearGradient>
          </defs>
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
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            width={44}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip
            {...tooltipStyles(theme)}
            formatter={(value: number) => [formatNumber(value, { decimals: 1, unit: '%' }), 'BSW']}
            labelFormatter={(label) => formatDate(String(label))}
          />
          <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 11, color: theme.text }} />
          <ReferenceLine
            y={80}
            stroke={SERIES_COLORS.breach}
            strokeDasharray="5 4"
            label={{
              value: '80% high water cut',
              position: 'insideTopRight',
              fill: SERIES_COLORS.breach,
              fontSize: 10,
            }}
          />
          <Area
            type="monotone"
            dataKey="bsw"
            name="BSW"
            stroke={SERIES_COLORS.bsw}
            strokeWidth={2}
            fill="url(#bswFill)"
            dot={{ r: 2.5, fill: SERIES_COLORS.bsw, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
