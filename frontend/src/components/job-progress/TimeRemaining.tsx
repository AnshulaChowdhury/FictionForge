/**
 * Time Remaining Component (Epic 10)
 *
 * Displays formatted time remaining for job completion
 */

import { Clock } from 'lucide-react'

interface TimeRemainingProps {
  seconds: number | null
  showIcon?: boolean
  className?: string
}

/**
 * Format seconds into human-readable time
 */
function formatTimeRemaining(seconds: number | null): string {
  if (!seconds || seconds <= 0) return 'Just now'

  if (seconds < 60) return `${Math.ceil(seconds)}s`

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.ceil(seconds % 60)

  if (minutes < 60) {
    if (remainingSeconds > 0 && minutes < 5) {
      return `${minutes}m ${remainingSeconds}s`
    }
    return `${minutes}m`
  }

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}m`
}

export function TimeRemaining({ seconds, showIcon = true, className }: TimeRemainingProps) {
  const formattedTime = formatTimeRemaining(seconds)

  return (
    <div className={`flex items-center text-sm text-muted-foreground ${className || ''}`}>
      {showIcon && <Clock className="mr-1 h-3.5 w-3.5" />}
      <span>{formattedTime} remaining</span>
    </div>
  )
}
