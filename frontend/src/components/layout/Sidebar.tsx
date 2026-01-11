/**
 * Sidebar navigation component.
 * Theme-aware styling with modern aesthetics.
 */

import { NavLink } from 'react-router-dom'
import { Home, Plus, Sparkles } from 'lucide-react'

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

export function Sidebar() {
  return (
    <aside className="w-72 bg-card border-r border-border flex flex-col">
      <nav className="flex-1 p-6 space-y-2">
        <div className="mb-6">
          <h3 className="text-xs text-accent font-semibold uppercase tracking-wider px-3 mb-3">
            Navigation
          </h3>
        </div>

        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `group flex items-start space-x-3 px-4 py-3.5 rounded-xl transition-smooth ${
                isActive
                  ? 'bg-primary text-primary-foreground shadow-medium'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                  isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent'
                } transition-smooth`} />
                <div className="flex flex-col">
                  <span className={`text-sm font-semibold ${
                    isActive ? 'text-primary-foreground' : 'text-foreground'
                  }`}>
                    {item.label}
                  </span>
                  <span className={`text-xs mt-0.5 ${
                    isActive ? 'text-primary-foreground/70' : 'text-muted-foreground'
                  }`}>
                    {item.description}
                  </span>
                </div>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer section */}
      <div className="p-6 border-t border-border">
        <div className="px-4 py-3 rounded-xl">
        </div>
      </div>
    </aside>
  )
}
