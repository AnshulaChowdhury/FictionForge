/**
 * Job Progress Bar Component (Epic 10)
 *
 * Enhanced progress bar showing percentage, stage, and time remaining
 */

import { Progress } from '@/components/ui/progress'
import { TimeRemaining } from './TimeRemaining'

interface JobProgressBarProps {
  progress: number
  stage?: string | null
  timeRemaining?: number | null
  showPercentage?: boolean
  showStage?: boolean
  showTimeRemaining?: boolean
  className?: string
}

export function JobProgressBar({
  progress,
  stage,
  timeRemaining,
  showPercentage = true,
  showStage = true,
  showTimeRemaining = true,
  className,
}: JobProgressBarProps) {
  return (
    <div className={`space-y-2 ${className || ''}`}>
      {/* Stage and Percentage */}
      {(showStage || showPercentage) && (
        <div className="flex items-center justify-between text-sm">
          {showStage && (
            <span className="text-muted-foreground font-medium">
              {stage || 'Processing...'}
            </span>
          )}
          {showPercentage && (
            <span className="text-muted-foreground font-semibold">{progress}%</span>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <Progress value={progress} className="h-2" />

      {/* Time Remaining */}
      {showTimeRemaining && timeRemaining && timeRemaining > 0 && (
        <TimeRemaining seconds={timeRemaining} className="text-xs" />
      )}
    </div>
  )
}
