import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Envelope } from '../../services/api'
import { EmptyState, formatNumber } from '../ui'
import { SERIES_COLORS, tooltipStyles, useChartTheme } from './chartTheme'

interface Props {
  data?: Envelope | null
  height?: number
}

/**
 * FTHP against gross liquid rate, with the three envelope bounds overlaid:
 * the THP curve, the minimum pressure for critical flow, and the erosional
 * rate limit. The latest test is plotted as a single point so the operating
 * position can be read against the envelope at a glance.
 */
export default function OperatingEnvelopeChart({ data, height = 340 }: Props) {
  const theme = useChartTheme()

  if (!data || !data.thp_curve?.length) {
    return (
      <EmptyState
        height={`h-[${height}px]`}
        title="No envelope available"
        description={
          data?.warnings?.[0] ??
          'This well has no workbook envelope and not enough test data to model one.'
        }
      />
    )
  }

  const curve = data.thp_curve
    .filter((p) => p.rate != null && p.thp != null)
    .map((p) => ({
      rate: p.rate,
      thp: p.thp,
      critical: p.critical_flow ?? data.critical_flow_pressure ?? null,
    }))

  const test = data.latest_test
  const testPoint =
    test?.gross_rate != null && test?.fthp != null
      ? [{ rate: test.gross_rate, thp: test.fthp }]
      : []

  const limit = data.erosional_rate_limit
  // Keep the erosional limit inside the plotted domain, otherwise its reference
  // line is silently clipped - which is what hid it in the previous version.
  const maxRate = Math.max(
    ...curve.map((p) => p.rate),
    ...testPoint.map((p) => p.rate),
    limit ?? 0,
  )
  const breached = data.within_erosional_limit === false

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={curve} margin={{ top: 16, right: 24, bottom: 28, left: 8 }}>
          <CartesianGrid stroke={theme.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            type="number"
            dataKey="rate"
            domain={[0, Math.ceil(maxRate * 1.06)]}
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            label={{
              value: 'Gross liquid rate (stb/d)',
              position: 'insideBottom',
              offset: -16,
              style: { fontSize: 11, fill: theme.text },
            }}
          />
          <YAxis
            stroke={theme.axis}
            tick={{ fontSize: 11, fill: theme.text }}
            tickLine={false}
            width={64}
            label={{
              value: 'FTHP (psig)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: theme.text, textAnchor: 'middle' },
            }}
          />
          <Tooltip
            {...tooltipStyles(theme)}
            formatter={(value: number, name: string) => [
              name.includes('rate') ? formatNumber(value, { unit: 'stb/d' }) : formatNumber(value, { unit: 'psig' }),
              name,
            ]}
            labelFormatter={(label) => `${formatNumber(Number(label))} stb/d`}
          />
          <Legend
            verticalAlign="top"
            height={28}
            wrapperStyle={{ fontSize: 11, color: theme.text }}
          />

          <Line
            type="monotone"
            dataKey="thp"
            name="THP curve"
            stroke={SERIES_COLORS.thp}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />

          {curve.some((p) => p.critical != null) && (
            <Line
              type="monotone"
              dataKey="critical"
              name="Critical flow limit"
              stroke={SERIES_COLORS.critical}
              strokeWidth={1.5}
              strokeDasharray="6 4"
              dot={false}
              isAnimationActive={false}
            />
          )}

          {limit != null && (
            <ReferenceLine
              x={limit}
              stroke={SERIES_COLORS.breach}
              strokeDasharray="5 4"
              strokeWidth={1.5}
              label={{
                value: `Erosional limit ${formatNumber(limit)}`,
                position: 'insideTopRight',
                fill: SERIES_COLORS.breach,
                fontSize: 10,
              }}
            />
          )}

          {testPoint.length > 0 && (
            <Scatter
              name="Latest test"
              data={testPoint}
              dataKey="thp"
              fill={breached ? SERIES_COLORS.breach : SERIES_COLORS.thp}
              shape="circle"
              r={7}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
