import { ReactNode } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import FieldsPage from './pages/Fields'
import WellsPage from './pages/Wells'
import WellDetailPage from './pages/WellDetail'
import UploadPage from './pages/Upload'
import { Card, EmptyState } from './components/ui'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // A 401 clears the session and redirects, so retrying it is pointless.
      retry: (failureCount, error: unknown) => {
        const status = (error as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403 || status === 404) return false
        return failureCount < 2
      },
    },
  },
})

function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function NotFound() {
  return (
    <Card>
      <EmptyState
        title="Page not found"
        description="That page does not exist."
        action={
          <Link to="/dashboard" className="btn-primary">
            Back to dashboard
          </Link>
        }
      />
    </Card>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public. The landing page is the entry point and stays reachable
              from inside the dashboard, so it is not gated. */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />

          {/* Everything below requires a session. */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="fields" element={<FieldsPage />} />
            <Route path="wells" element={<WellsPage />} />
            <Route path="wells/:wellId" element={<WellDetailPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>

          {/* Anything else falls back to the landing page rather than a dead
              end, since an unauthenticated visitor cannot see the dashboard's
              own 404. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
