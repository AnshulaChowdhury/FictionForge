/**
 * Inline Job Progress Component (Epic 10)
 *
 * Displays progress inline within a sub-chapter card
 * Automatically subscribes to WebSocket updates for the specific job
 */

import { useEffect, useState } from 'react'
import { useWebSocket, type JobProgressMessage } from '@/hooks/useWebSocket'
import { JobProgressBar } from './JobProgressBar'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { X, AlertCircle } from 'lucide-react'

interface InlineJobProgressProps {
  jobId: string
  initialProgress?: number
  initialStage?: string | null
  initialTimeRemaining?: number | null
  onCancel?: () => void
  onComplete?: () => void
  onError?: (error: string) => void
  className?: string
}

export function InlineJobProgress({
  jobId,
  initialProgress = 0,
  initialStage = null,
  initialTimeRemaining = null,
  onCancel,
  onComplete,
  onError,
  className,
}: InlineJobProgressProps) {
  const [progress, setProgress] = useState(initialProgress)
  const [stage, setStage] = useState(initialStage)
  const [timeRemaining, setTimeRemaining] = useState(initialTimeRemaining)
  const [error, setError] = useState<string | null>(null)

  const { subscribe } = useWebSocket({ autoConnect: true })

  useEffect(() => {
    // Subscribe to progress updates for this specific job
    const unsubscribeProgress = subscribe<JobProgressMessage>('job_progress', (message) => {
      if (message.job_id === jobId) {
        setProgress(message.progress_percentage)
        setStage(message.stage)
        setTimeRemaining(message.time_remaining_seconds)
      }
    })

    const unsubscribeCompleted = subscribe('job_completed', (message) => {
      if (message.job_id === jobId) {
        setProgress(100)
        setStage('Complete')
        onComplete?.()
      }
    })

    const unsubscribeFailed = subscribe('job_failed', (message) => {
      if (message.job_id === jobId) {
        setError(message.error_message)
        onError?.(message.error_message)
      }
    })

    return () => {
      unsubscribeProgress()
      unsubscribeCompleted()
      unsubscribeFailed()
    }
  }, [jobId, subscribe, onComplete, onError])

  if (error) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>{error}</span>
          {onCancel && (
            <Button variant="ghost" size="sm" onClick={onCancel}>
              Dismiss
            </Button>
          )}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className={`space-y-2 ${className || ''}`}>
      <div className="flex items-center justify-between">
        <JobProgressBar
          progress={progress}
          stage={stage}
          timeRemaining={timeRemaining}
          showPercentage={true}
          showStage={true}
          showTimeRemaining={true}
          className="flex-1"
        />
        {onCancel && progress < 100 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            className="ml-3 text-red-600 hover:text-red-700"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
