/**
 * Theme store for managing app themes.
 * Supports: Ink & Paper, Night Writer, Minimalist
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeId = 'ink-paper' | 'night-writer' | 'minimalist'

export interface Theme {
  id: ThemeId
  name: string
  description: string
  icon: string
}

export const themes: Theme[] = [
  {
    id: 'ink-paper',
    name: 'Ink & Paper',
    description: 'Warm, classic literary feel',
    icon: '📜',
  },
  {
    id: 'night-writer',
    name: 'Night Writer',
    description: 'Dark mode for late sessions',
    icon: '🌙',
  },
  {
    id: 'minimalist',
    name: 'Minimalist',
    description: 'Clean whites, refined elegance',
    icon: '✨',
  },
]

interface ThemeState {
  theme: ThemeId
  setTheme: (theme: ThemeId) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'ink-paper',
      setTheme: (theme) => {
        // Update the data-theme attribute on the document
        document.documentElement.setAttribute('data-theme', theme)
        set({ theme })
      },
    }),
    {
      name: 'fiction-forge-theme',
      onRehydrateStorage: () => (state) => {
        // Apply theme on rehydration
        if (state?.theme) {
          document.documentElement.setAttribute('data-theme', state.theme)
        }
      },
    }
  )
)

// Initialize theme on load
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('fiction-forge-theme')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      if (parsed.state?.theme) {
        document.documentElement.setAttribute('data-theme', parsed.state.theme)
      }
    } catch {
      // Default theme will be applied
    }
  }
}
