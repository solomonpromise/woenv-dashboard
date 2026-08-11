import { useEffect, useState } from 'react'

/**
 * Recharts renders SVG with literal colour props, so it cannot read the CSS
 * custom properties that drive the rest of the theme. This hook resolves the
 * current palette to concrete values and re-resolves it when the theme flips.
 */
export interface ChartTheme {
  grid: string
  axis: string
  tooltipBg: string
  tooltipBorder: string
  text: string
  isDark: boolean
}

function read(): ChartTheme {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    isDark,
    grid: isDark ? '#273244' : '#e2e8f0',
    axis: isDark ? '#7a889c' : '#94a3b8',
    text: isDark ? '#a3b0c2' : '#475569',
    tooltipBg: isDark ? '#18202f' : '#ffffff',
    tooltipBorder: isDark ? '#38465c' : '#cbd5e1',
  }
}

export function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(read)

  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(read()))
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })
    return () => observer.disconnect()
  }, [])

  return theme
}

/** Shared tooltip styling so every chart reads the same. */
export function tooltipStyles(theme: ChartTheme) {
  return {
    contentStyle: {
      backgroundColor: theme.tooltipBg,
      border: `1px solid ${theme.tooltipBorder}`,
      borderRadius: '0.5rem',
      fontSize: '0.75rem',
      boxShadow: '0 4px 12px -2px rgb(0 0 0 / 0.12)',
      color: theme.text,
    },
    labelStyle: { color: theme.text, fontWeight: 600, marginBottom: 2 },
    itemStyle: { color: theme.text, padding: '1px 0' },
  }
}

export const SERIES_COLORS = {
  oil: '#059669',
  water: '#0ea5e9',
  gas: '#f59e0b',
  bsw: '#0ea5e9',
  gor: '#059669',
  glr: '#f59e0b',
  thp: '#2563eb',
  critical: '#f59e0b',
  breach: '#ef4444',
  test: '#ef4444',
} as const
