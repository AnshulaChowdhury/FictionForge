/**
 * Back button for hierarchical navigation.
 */

import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface BackButtonProps {
  label: string
  to: string
  isCollapsed?: boolean
}

export function BackButton({ label, to, isCollapsed = false }: BackButtonProps) {
  const navigate = useNavigate()

  return (
    <button
      onClick={() => navigate(to)}
      className={cn(
        'flex items-center gap-1.5 text-xs text-muted-foreground',
        'hover:text-foreground transition-colors',
        'px-2.5 py-1.5 rounded hover:bg-muted',
        isCollapsed && 'justify-center px-2'
      )}
      title={isCollapsed ? `Back to ${label}` : undefined}
    >
      <ArrowLeft className="w-3.5 h-3.5 flex-shrink-0" />
      {!isCollapsed && <span>{label}</span>}
    </button>
  )
}
