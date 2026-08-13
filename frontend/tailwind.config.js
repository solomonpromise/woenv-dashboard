/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Driven by CSS custom properties so light and dark themes share one
        // set of utility classes.
        surface: {
          DEFAULT: 'rgb(var(--surface) / <alpha-value>)',
          raised: 'rgb(var(--surface-raised) / <alpha-value>)',
          sunken: 'rgb(var(--surface-sunken) / <alpha-value>)',
        },
        edge: {
          DEFAULT: 'rgb(var(--edge) / <alpha-value>)',
          strong: 'rgb(var(--edge-strong) / <alpha-value>)',
        },
        content: {
          DEFAULT: 'rgb(var(--content) / <alpha-value>)',
          muted: 'rgb(var(--content-muted) / <alpha-value>)',
          subtle: 'rgb(var(--content-subtle) / <alpha-value>)',
        },
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Semantic colours for well state and envelope breaches.
        flowing: '#10b981',
        closed: '#94a3b8',
        breach: '#ef4444',
        caution: '#f59e0b',
        oil: '#059669',
        water: '#0ea5e9',
        gas: '#f59e0b',
      },
      fontFamily: {
        sans: ['Inter var', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        /*
         * Elevation is tinted with the theme's shadow hue rather than pure
         * black. Neutral black over a blue-tinted surface reads as grime; a
         * hue-matched shadow reads as depth. Each level stacks a tight contact
         * shadow with a wider ambient one.
         */
        card: '0 1px 2px -1px hsl(var(--shadow-hue) / 0.10), 0 2px 6px -2px hsl(var(--shadow-hue) / 0.08)',
        raised:
          '0 2px 4px -2px hsl(var(--shadow-hue) / 0.12), 0 8px 20px -6px hsl(var(--shadow-hue) / 0.16)',
        floating:
          '0 4px 8px -4px hsl(var(--shadow-hue) / 0.16), 0 20px 40px -12px hsl(var(--shadow-hue) / 0.24)',
        inset: 'inset 0 1px 2px 0 hsl(var(--shadow-hue) / 0.06)',
        // Coloured shadows so a primary action looks lit rather than painted.
        'btn-primary': '0 1px 2px 0 rgb(29 78 216 / 0.30), 0 6px 16px -6px rgb(37 99 235 / 0.55)',
        'btn-primary-hover':
          '0 2px 4px 0 rgb(29 78 216 / 0.32), 0 10px 24px -6px rgb(37 99 235 / 0.65)',
        'btn-danger': '0 1px 2px 0 rgb(185 28 28 / 0.30), 0 6px 16px -6px rgb(239 68 68 / 0.50)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'rise-in': 'riseIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both',
        shimmer: 'shimmer 1.6s ease-in-out infinite',
        'pulse-ring': 'pulseRing 2.4s ease-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        riseIn: {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%, 100%': { opacity: '0.45' },
          '50%': { opacity: '0.85' },
        },
        // Radiating ring on the breaching well marker in the hero diagram.
        pulseRing: {
          '0%': { transform: 'scale(0.8)', opacity: '0.7' },
          '70%, 100%': { transform: 'scale(2.2)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
