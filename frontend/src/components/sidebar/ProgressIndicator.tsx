/**
 * Progress indicator component for word count display.
 */

import { cn } from '@/lib/utils'

interface ProgressIndicatorProps {
  current: number
  target: number
  showBar?: boolean
  isCollapsed?: boolean
  className?: string
}

export function ProgressIndicator({
  current,
  target,
  showBar = false,
  isCollapsed = false,
  className,
}: ProgressIndicatorProps) {
  const percentage = target > 0 ? Math.min((current / target) * 100, 100) : 0
  const formattedCurrent = current.toLocaleString()
  const formattedTarget = target.toLocaleString()

  if (isCollapsed) {
    return null
  }

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {formattedCurrent} / {formattedTarget}
        </span>
        <span>{Math.round(percentage)}%</span>
      </div>

      {showBar && (
        <div className="w-full bg-muted rounded h-1">
          <div
            className={cn(
              'h-1 rounded transition-all duration-300',
              percentage >= 100 ? 'bg-success' : 'bg-accent'
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  )
}
