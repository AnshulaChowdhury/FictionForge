/**
 * Reusable navigation item component with active state highlighting.
 * Theme-aware styling.
 */

import { NavLink } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavigationItemProps {
  to: string
  icon?: LucideIcon
  label: string
  isCollapsed?: boolean
  onClick?: () => void
  badge?: string | number
  rightIcon?: LucideIcon
}

export function NavigationItem({
  to,
  icon: Icon,
  label,
  isCollapsed = false,
  onClick,
  badge,
  rightIcon: RightIcon,
}: NavigationItemProps) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          'group flex items-center transition-colors rounded',
          isCollapsed ? 'px-2 py-2 justify-center' : 'px-2.5 py-2 gap-2.5',
          isActive
            ? 'bg-accent/10 text-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        )
      }
      title={isCollapsed ? label : undefined}
    >
      {({ isActive }) => (
        <>
          {Icon && (
            <Icon
              className={cn(
                'flex-shrink-0 w-4 h-4',
                isActive ? 'text-accent' : 'text-muted-foreground'
              )}
            />
          )}

          {!isCollapsed && (
            <div className="flex items-center justify-between flex-1 min-w-0 gap-2">
              <span className="text-sm truncate">
                {label}
              </span>
              {badge && (
                <span className="px-1.5 py-0.5 text-xs rounded bg-muted text-muted-foreground">
                  {badge}
                </span>
              )}
              {RightIcon && (
                <RightIcon className="w-3.5 h-3.5 flex-shrink-0 text-muted-foreground" />
              )}
            </div>
          )}
        </>
      )}
    </NavLink>
  )
}
