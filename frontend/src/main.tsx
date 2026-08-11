import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { preferredTheme, useThemeStore } from './stores/themeStore'
import './index.css'

// Apply the stored theme before first paint so the page never flashes light
// then swaps to dark. Zustand's persist rehydration also calls this, but that
// happens a tick later.
const stored = (() => {
  try {
    return JSON.parse(localStorage.getItem('theme-storage') ?? '')?.state?.theme
  } catch {
    return null
  }
})()
useThemeStore.getState().setTheme(stored ?? preferredTheme())

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-surface-sunken p-6">
          <div className="card card-pad max-w-lg">
            <h1 className="text-sm font-semibold text-breach">Something went wrong</h1>
            <p className="mt-1 text-xs text-content-muted">
              The dashboard hit an unexpected error and could not continue.
            </p>
            <pre className="mt-4 max-h-64 overflow-auto rounded-lg bg-surface-sunken p-3 font-mono text-2xs text-content-muted">
              {this.state.error.message}
              {'\n\n'}
              {this.state.error.stack}
            </pre>
            <button onClick={() => window.location.reload()} className="btn-primary mt-4">
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
