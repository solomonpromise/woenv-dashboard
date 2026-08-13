import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIState {
  /** Desktop only. The mobile drawer always renders in full. */
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
}

/**
 * Chrome preferences that should outlive a reload. Kept separate from the
 * theme store so an unrelated preference does not force a re-render of every
 * themed component.
 */
export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set({ sidebarCollapsed: !get().sidebarCollapsed }),
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
    }),
    { name: 'ui-storage' },
  ),
)
