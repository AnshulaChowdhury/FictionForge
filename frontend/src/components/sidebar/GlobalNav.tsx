/**
 * Global navigation (Level 0) - shown when no trilogy context is active.
 * Theme-aware styling.
 */

import { Home, Plus, Sparkles } from 'lucide-react'
import { NavigationItem } from './NavigationItem'

interface GlobalNavProps {
  isCollapsed?: boolean
}

const navItems = [
  {
    to: '/dashboard',
    icon: Home,
    label: 'Dashboard',
    description: 'View all your trilogies',
  },
  {
    to: '/generation-queue',
    icon: Sparkles,
    label: 'Generation Queue',
    description: 'Monitor AI generation',
  },
  {
    to: '/trilogy/create',
    icon: Plus,
    label: 'Create Trilogy',
    description: 'Start a new project',
  },
]

export function GlobalNav({ isCollapsed = false }: GlobalNavProps) {
  return (
    <nav className="space-y-0.5">
      {navItems.map((item) => (
        <NavigationItem
          key={item.to}
          to={item.to}
          icon={item.icon}
          label={item.label}
          isCollapsed={isCollapsed}
        />
      ))}
    </nav>
  )
}
