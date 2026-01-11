/**
 * Hook to manage sidebar collapse state with localStorage persistence.
 */

import { useState, useEffect } from 'react'

const STORAGE_KEY = 'sidebar-collapsed'

export function useSidebarCollapse() {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : false
    } catch {
      return false
    }
  })

  // Persist collapse state to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(isCollapsed))
    } catch {
      // Silently fail if localStorage is not available
    }
  }, [isCollapsed])

  const toggle = () => setIsCollapsed((prev) => !prev)

  return {
    isCollapsed,
    setIsCollapsed,
    toggle,
  }
}
