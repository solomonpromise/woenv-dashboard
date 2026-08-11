import { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
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
          <a href="/" className="btn-primary">
            Back to dashboard
          </a>
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
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
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
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
