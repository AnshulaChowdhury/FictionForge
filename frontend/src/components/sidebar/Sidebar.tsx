/**
 * Context-aware sidebar navigation component.
 * Automatically adapts to current location in trilogy hierarchy.
 * Supports collapse toggle and drag-to-resize.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { Menu, X, ListChecks, GripVertical } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useSidebarContext } from './hooks/useSidebarContext'
import { useSidebarCollapse } from './hooks/useSidebarCollapse'
import { GlobalNav } from './GlobalNav'
import { TrilogyNav } from './TrilogyNav'
import { BookNav } from './BookNav'
import { ChapterNav } from './ChapterNav'

const MIN_WIDTH = 200
const MAX_WIDTH = 400
const COLLAPSED_WIDTH = 64
const DEFAULT_WIDTH = 288 // w-72 = 18rem = 288px
const STORAGE_KEY = 'sidebar-width'

export function Sidebar() {
  const context = useSidebarContext()
  const { isCollapsed, toggle, setIsCollapsed } = useSidebarCollapse()
  const navigate = useNavigate()

  // Resizable width state
  const [width, setWidth] = useState<number>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? parseInt(stored, 10) : DEFAULT_WIDTH
    } catch {
      return DEFAULT_WIDTH
    }
  })

  const [isResizing, setIsResizing] = useState(false)
  const sidebarRef = useRef<HTMLElement>(null)

  // Persist width to localStorage
  useEffect(() => {
    if (!isCollapsed) {
      try {
        localStorage.setItem(STORAGE_KEY, String(width))
      } catch {
        // Silently fail
      }
    }
  }, [width, isCollapsed])

  // Handle mouse move during resize
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return

    const newWidth = e.clientX
    if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
      setWidth(newWidth)
    } else if (newWidth < MIN_WIDTH - 50) {
      // Snap to collapsed if dragged very small
      setIsCollapsed(true)
      setIsResizing(false)
    }
  }, [isResizing, setIsCollapsed])

  // Handle mouse up to stop resize
  const handleMouseUp = useCallback(() => {
    setIsResizing(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }, [])

  // Add/remove event listeners for resize
  useEffect(() => {
    if (isResizing) {
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing, handleMouseMove, handleMouseUp])

  // Start resize
  const startResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  // Render appropriate navigation based on context level
  const renderNavigation = () => {
    switch (context.level) {
      case 'chapter':
        if (!context.chapterId) return <GlobalNav isCollapsed={isCollapsed} />
        return <ChapterNav chapterId={context.chapterId} isCollapsed={isCollapsed} />

      case 'book':
        if (!context.bookId) return <GlobalNav isCollapsed={isCollapsed} />
        return <BookNav bookId={context.bookId} isCollapsed={isCollapsed} />

      case 'trilogy':
        if (!context.trilogyId) return <GlobalNav isCollapsed={isCollapsed} />
        return <TrilogyNav trilogyId={context.trilogyId} isCollapsed={isCollapsed} />

      case 'global':
      default:
        return <GlobalNav isCollapsed={isCollapsed} />
    }
  }

  // Calculate current width
  const currentWidth = isCollapsed ? COLLAPSED_WIDTH : width

  return (
    <aside
      ref={sidebarRef}
      style={{ width: currentWidth }}
      className={cn(
        'bg-card border-r border-border flex flex-col relative',
        'transition-[width] duration-200 ease-in-out',
        isCollapsed && 'sidebar-collapsed'
      )}
    >
      {/* Collapse toggle - minimal header */}
      <div className={cn(
        'flex items-center p-3 border-b border-border',
        isCollapsed ? 'justify-center' : 'justify-end'
      )}>
        <button
          onClick={toggle}
          className="p-1.5 rounded hover:bg-muted transition-colors"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <Menu className="w-4 h-4 text-muted-foreground" />
          ) : (
            <X className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      {/* Navigation content */}
      <nav className="flex-1 p-2 overflow-y-auto overflow-x-hidden">
        {renderNavigation()}
      </nav>

      {/* Footer - Generation Queue */}
      <div className="p-2 border-t border-border">
        <button
          onClick={() => navigate('/generation-queue')}
          className={cn(
            'w-full flex items-center gap-2 px-2.5 py-2 rounded',
            'hover:bg-muted transition-colors',
            'text-sm text-muted-foreground hover:text-foreground',
            isCollapsed && 'justify-center px-2'
          )}
          title="Generation Queue"
        >
          <ListChecks className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="truncate">Generation Queue</span>}
        </button>
      </div>

      {/* Resize handle */}
      {!isCollapsed && (
        <div
          onMouseDown={startResize}
          className={cn(
            'absolute top-0 right-0 w-1 h-full cursor-col-resize',
            'hover:bg-accent/50 transition-colors',
            'group flex items-center justify-center',
            isResizing && 'bg-accent/50'
          )}
          title="Drag to resize"
        >
          <div className={cn(
            'absolute right-0 top-1/2 -translate-y-1/2 w-4 h-8',
            'flex items-center justify-center',
            'opacity-0 group-hover:opacity-100 transition-opacity',
            isResizing && 'opacity-100'
          )}>
            <GripVertical className="w-3 h-3 text-muted-foreground" />
          </div>
        </div>
      )}
    </aside>
  )
}
