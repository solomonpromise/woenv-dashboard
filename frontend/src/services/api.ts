import axios from 'axios'

// Default to the dev-server proxy path. When VITE_API_URL is supplied it must
// be an origin only - the /api/v1 prefix is appended here so a misconfigured
// env var cannot silently strip it and 404 every request.
const configured = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
export const API_BASE_URL = configured ? `${configured}/api/v1` : '/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

const AUTH_STORAGE_KEY = 'auth-storage'

export function readStoredToken(): string | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)?.state?.token ?? null
  } catch {
    return null
  }
}

api.interceptors.request.use((config) => {
  const token = readStoredToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only bounce to the login screen for an expired/invalid session, and only
    // when we are not already there - otherwise a failed login request would
    // reload the page and discard its own error message.
    if (error.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      localStorage.removeItem(AUTH_STORAGE_KEY)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

/** Pulls a readable message out of an axios error for display. */
export function errorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
    if (error.code === 'ERR_NETWORK') return 'Cannot reach the API. Is the backend running?'
    return error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

export interface User {
  id: number
  email: string
  username: string
  full_name?: string | null
  role: string
  is_active?: boolean
}

export interface Field {
  id: number
  name: string
  code: string
  location?: string | null
}

export interface Well {
  id: number
  field_id: number
  name: string
  well_type?: string | null
  prod_method?: string | null
  status?: string | null
  bean_model?: string | null
  is_active: boolean
}

export interface TestRecord {
  id: number
  well_id: number
  test_start: string
  status?: string | null
  result_status?: string | null
  fthp_psig: number | null
  choke_size: number | null
  gross_rate_stbd: number | null
  oil_rate_stbd: number | null
  water_rate_stbd: number | null
  gas_rate_mscfd: number | null
  bsw_percent: number | null
  fgor_scfstb: number | null
  glr_scfstb: number | null
  sep_pressure: number | null
  sep_temp: number | null
  sand_pptb: number | null
}

export interface EnvelopePoint {
  rate: number
  thp: number
  flp?: number | null
  critical_flow?: number | null
}

export interface Envelope {
  well_id: number
  well_name: string
  field_id: number
  status?: string | null
  bean_model?: string | null
  bean_model_applied?: string | null
  erosional_rate_limit: number | null
  erosional_limit_source: string
  erosional_velocity: number | null
  mixture_density: number | null
  c_factor: number | null
  thp_curve: EnvelopePoint[]
  thp_curve_source: string
  critical_flow_pressure: number | null
  is_critical_flow: boolean | null
  predicted_rate: number | null
  within_erosional_limit?: boolean
  erosional_utilisation?: number
  latest_test: {
    date: string | null
    fthp: number | null
    gross_rate: number | null
    oil_rate: number | null
    water_rate: number | null
    bsw_percent: number | null
    gor: number | null
    glr: number | null
    choke_size: number | null
    sep_pressure: number | null
  } | null
  warnings: string[]
}

export interface Overview {
  total_wells: number
  flowing_wells: number
  closed_wells: number
  tested_wells: number
  gross_rate_stbd: number
  oil_rate_stbd: number
  water_rate_stbd: number
  gas_rate_mscfd: number
  avg_bsw_percent: number | null
}

export interface FieldStats {
  field_id: number
  name: string
  code: string
  total_wells: number
  flowing_wells: number
  closed_wells: number
  gross_rate_stbd: number
  oil_rate_stbd: number
  avg_bsw_percent: number | null
}

export interface EnvelopeAlert {
  well_id: number
  well_name: string
  field_id: number
  status?: string | null
  test_start: string | null
  gross_rate_stbd: number | null
  erosional_limit: number | null
  utilisation: number | null
  fthp_psig: number | null
  sep_pressure: number | null
  reasons: string[]
}

export interface UploadResult {
  filename: string
  field_code: string
  wells_created: number
  wells_updated: number
  tests_created: number
  tests_skipped: number
  erosionals_created: number
  envelope_points: number
  errors: string[]
  status: string
}

/* -------------------------------------------------------------------------- */
/* Endpoints                                                                  */
/* -------------------------------------------------------------------------- */

export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string; token_type: string }>(
      '/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    ),
  me: () => api.get<User>('/auth/me'),
  register: (data: Record<string, unknown>) => api.post<User>('/auth/register', data),
}

export const fieldsApi = {
  getAll: () => api.get<Field[]>('/fields/'),
  getById: (id: number) => api.get<Field>(`/fields/${id}`),
  create: (data: Partial<Field>) => api.post<Field>('/fields/', data),
  update: (id: number, data: Partial<Field>) => api.put<Field>(`/fields/${id}`, data),
  remove: (id: number) => api.delete(`/fields/${id}`),
}

export const wellsApi = {
  getAll: (params?: { field_id?: number; status?: string; limit?: number; skip?: number }) =>
    api.get<Well[]>('/wells/', { params: { limit: 500, ...params } }),
  getById: (id: number) => api.get<Well>(`/wells/${id}`),
  getHistory: (id: number, limit = 20) =>
    api.get<TestRecord[]>(`/wells/${id}/history`, { params: { limit } }),
  create: (data: Partial<Well>) => api.post<Well>('/wells/', data),
  update: (id: number, data: Partial<Well>) => api.put<Well>(`/wells/${id}`, data),
  remove: (id: number) => api.delete(`/wells/${id}`),
}

export const envelopesApi = {
  getByWellId: (wellId: number) => api.get<Envelope>(`/envelopes/${wellId}`),
  compute: (wellId: number) => api.post<Envelope>(`/envelopes/compute/${wellId}`),
}

export const statsApi = {
  overview: (fieldId?: number) =>
    api.get<Overview>('/stats/overview', { params: fieldId ? { field_id: fieldId } : undefined }),
  fields: () => api.get<FieldStats[]>('/stats/fields'),
  alerts: (fieldId?: number) =>
    api.get<EnvelopeAlert[]>('/stats/envelope-alerts', {
      params: fieldId ? { field_id: fieldId } : undefined,
    }),
}

export const uploadApi = {
  uploadExcel: (file: File, fieldCode = '') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('field_code', fieldCode)
    return api.post<UploadResult>('/upload/excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
