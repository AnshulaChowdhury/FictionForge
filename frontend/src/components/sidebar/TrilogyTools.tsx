/**
 * Quick access to trilogy-scoped tools.
 */

import { Users, Globe, BarChart3 } from 'lucide-react'
import { NavigationItem } from './NavigationItem'

interface TrilogyToolsProps {
  trilogyId: string
  isCollapsed?: boolean
}

export function TrilogyTools({ trilogyId, isCollapsed = false }: TrilogyToolsProps) {
  const tools = [
    {
      to: `/trilogy/${trilogyId}/characters`,
      icon: Users,
      label: 'Characters',
      description: 'Character voices',
    },
    {
      to: `/trilogy/${trilogyId}/world-rules`,
      icon: Globe,
      label: 'World Rules',
      description: 'Consistency rules',
    },
    {
      to: `/trilogy/${trilogyId}/rule-analytics`,
      icon: BarChart3,
      label: 'Rule Analytics',
      description: 'Rule accuracy',
    },
  ]

  return (
    <div className="space-y-0.5">
      {tools.map((tool) => (
        <NavigationItem
          key={tool.to}
          to={tool.to}
          icon={tool.icon}
          label={tool.label}
          isCollapsed={isCollapsed}
        />
      ))}
    </div>
  )
}
