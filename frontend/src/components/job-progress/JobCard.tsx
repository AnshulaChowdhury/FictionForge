/**
 * Job Card Component (Epic 10)
 *
 * Displays a complete job card with status, progress, and actions
 */

import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StatusBadge, type JobStatus } from './StatusBadge'
import { JobProgressBar } from './JobProgressBar'
import { FileText, User, X, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { GenerationJobListItem } from '@/api/generationJobs'

interface JobCardProps {
  job: GenerationJobListItem
  onCancel?: (jobId: string) => void
  onViewContent?: (subChapterId: string) => void
  showActions?: boolean
  className?: string
}

export function JobCard({
  job,
  onCancel,
  onViewContent,
  showActions = true,
  className,
}: JobCardProps) {
  const isActive = job.status === 'in_progress' || job.status === 'queued'
  const isCompleted = job.status === 'completed'
  const canCancel = job.can_cancel && isActive && onCancel

  return (
    <Card className={`overflow-hidden transition-all ${className || ''}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            {/* Sub-chapter Title */}
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-semibold text-base line-clamp-1">
                {job.sub_chapter_title || 'Untitled Sub-chapter'}
              </h3>
            </div>

            {/* Chapter Title */}
            {job.chapter_title && (
              <p className="text-sm text-muted-foreground line-clamp-1">
                Chapter: {job.chapter_title}
              </p>
            )}

            {/* Character Name */}
            {job.character_name && (
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <User className="h-3.5 w-3.5" />
                <span>{job.character_name}</span>
              </div>
            )}
          </div>

          {/* Status Badge */}
          <StatusBadge status={job.status as JobStatus} />
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        {/* Progress Bar (only for active jobs) */}
        {isActive && (
          <JobProgressBar
            progress={job.progress_percentage}
            stage={job.stage}
            timeRemaining={job.time_remaining_seconds}
          />
        )}

        {/* Completed Info */}
        {isCompleted && job.word_count && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Generated:</span>
            <span className="font-semibold">{job.word_count.toLocaleString()} words</span>
          </div>
        )}

        {/* Metadata */}
        <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
          {/* Created Time */}
          <span>
            Started {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
          </span>

          {/* Queue Position */}
          {job.queue_position && job.queue_position > 0 && (
            <span className="flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-muted-foreground" />
              Position {job.queue_position} in queue
            </span>
          )}
        </div>
      </CardContent>

      {/* Actions */}
      {showActions && (canCancel || (isCompleted && onViewContent)) && (
        <CardFooter className="pt-3 border-t flex gap-2">
          {/* Cancel Button */}
          {canCancel && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onCancel(job.id)}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <X className="mr-1.5 h-3.5 w-3.5" />
              Cancel
            </Button>
          )}

          {/* View Content Button */}
          {isCompleted && onViewContent && (
            <Button
              variant="default"
              size="sm"
              onClick={() => onViewContent(job.sub_chapter_id)}
              className="ml-auto"
            >
              <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
              View Content
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  )
}
