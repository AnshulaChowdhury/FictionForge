/**
 * Hook to detect current sidebar context from URL.
 * Determines navigation level and extracts relevant IDs.
 */

import { useLocation, useParams } from 'react-router-dom'

export type SidebarLevel = 'global' | 'trilogy' | 'book' | 'chapter'

export interface SidebarContext {
  level: SidebarLevel
  trilogyId?: string
  bookId?: string
  chapterId?: string
}

export function useSidebarContext(): SidebarContext {
  const location = useLocation()
  const params = useParams<{
    trilogyId?: string
    bookId?: string
    chapterId?: string
  }>()

  // Detect level based on pathname
  const pathname = location.pathname

  // Chapter level: /chapter/:chapterId/sub-chapters
  if (pathname.includes('/chapter/') && pathname.includes('/sub-chapters')) {
    return {
      level: 'chapter',
      chapterId: params.chapterId,
    }
  }

  // Book level: /book/:bookId/chapters
  if (pathname.includes('/book/') && pathname.includes('/chapters')) {
    return {
      level: 'book',
      bookId: params.bookId,
    }
  }

  // Trilogy level: /trilogy/:trilogyId/*
  if (pathname.includes('/trilogy/') && params.trilogyId) {
    return {
      level: 'trilogy',
      trilogyId: params.trilogyId,
    }
  }

  // Global level: dashboard, generation-queue, create
  return {
    level: 'global',
  }
}
