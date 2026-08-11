import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../services/api'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setSession: (token: string) => void
  setUser: (user: User) => void
  logout: () => void
  /** True when the signed-in user may create or modify records. */
  canEdit: () => boolean
  /** True when the signed-in user may delete records or manage fields. */
  isAdmin: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      // The token arrives first; the real identity is fetched from /auth/me
      // straight after. Previously the app invented a user object with a
      // hardcoded 'engineer' role, so an admin could never see admin controls.
      setSession: (token) => set({ token, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),

      canEdit: () => ['admin', 'engineer'].includes(get().user?.role ?? ''),
      isAdmin: () => get().user?.role === 'admin',
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
