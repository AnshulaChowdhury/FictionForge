/**
 * Generation Queue Dashboard Page (Epic 10)
 *
 * Displays all active and pending content generation jobs with real-time updates
 */

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, RefreshCw, Sparkles } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

import { getGenerationJobs, cancelJob } from '@/api/generationJobs'
import {
  useWebSocket,
  type JobProgressMessage,
  type JobCompletedMessage,
  type JobFailedMessage
} from '@/hooks/useWebSocket'
import { JobCard } from '@/components/job-progress'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export default function GenerationQueuePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  // Fetch all jobs (no status filter = all jobs including completed/failed)
  const {
    data: jobsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['generation-jobs', 'all'],
    queryFn: () => getGenerationJobs(undefined, 100), // Fetch up to 100 jobs for history
    refetchInterval: 5000, // Fallback polling every 5s
  })

  // Cancel job mutation
  const cancelMutation = useMutation({
    mutationFn: cancelJob,
    onSuccess: () => {
      toast({
        description: 'Job cancelled successfully',
      })
      queryClient.invalidateQueries({ queryKey: ['generation-jobs'] })
    },
    onError: (error: any) => {
      toast({
        description: error.response?.data?.detail || 'Failed to cancel job',
        variant: 'destructive',
      })
    },
  })

  // WebSocket for real-time updates
  const { status: wsStatus, subscribe } = useWebSocket({
    autoConnect: true,
    onConnect: () => {
      console.log('WebSocket connected')
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected')
    },
    onError: () => {
      console.log('WebSocket error')
    },
  })

  // Subscribe to job progress updates
  useEffect(() => {
    const unsubscribeProgress = subscribe<JobProgressMessage>('job_progress', (message) => {
      // Update job in cache
      queryClient.setQueryData<typeof jobsData>(
        ['generation-jobs', 'active'],
        (old) => {
          if (!old) return old

          return {
            ...old,
            jobs: old.jobs.map((job) =>
              job.id === message.job_id
                ? {
                    ...job,
                    status: message.status,
                    stage: message.stage,
                    progress_percentage: message.progress_percentage,
                    estimated_completion: message.estimated_completion,
                    time_remaining_seconds: message.time_remaining_seconds,
                  }
                : job
            ),
          }
        }
      )
    })

    const unsubscribeCompleted = subscribe<JobCompletedMessage>('job_completed', (message) => {
      toast({
        title: 'Generation Complete',
        description: message.message,
      })
      // Refetch to update list
      refetch()
    })

    const unsubscribeFailed = subscribe<JobFailedMessage>('job_failed', (message) => {
      toast({
        title: 'Generation Failed',
        description: message.message,
        variant: 'destructive',
      })
      // Refetch to update list
      refetch()
    })

    return () => {
      unsubscribeProgress()
      unsubscribeCompleted()
      unsubscribeFailed()
    }
  }, [subscribe, queryClient, refetch, toast])

  const handleCancel = (jobId: string) => {
    if (confirm('Are you sure you want to cancel this generation job?')) {
      cancelMutation.mutate(jobId)
    }
  }

  const handleViewContent = (subChapterId: string) => {
    // Find the job to get chapter_id for navigation
    const job = jobs.find((j) => j.sub_chapter_id === subChapterId)
    if (job?.chapter_id) {
      // Navigate to sub-chapters page with query parameter to auto-open content dialog
      navigate(`/chapter/${job.chapter_id}/sub-chapters?viewSubChapter=${subChapterId}`)
    } else {
      // Fallback to dashboard if chapter_id not found
      toast({
        description: 'Unable to navigate to content - chapter information not available',
        variant: 'destructive',
      })
      navigate('/dashboard')
    }
  }

  const jobs = jobsData?.jobs || []
  const activeJobs = jobs.filter((job) => job.status === 'in_progress' || job.status === 'queued')
  const completedJobs = jobs.filter((job) => job.status === 'completed')
  const failedJobs = jobs.filter((job) => job.status === 'failed' || job.status === 'cancelled')

  return (
    <div className="container mx-auto py-6 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl text-foreground font-semibold flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-primary" />
              Generation History
            </h1>
            <p className="text-muted-foreground mt-1">
              Track all content generation jobs with real-time updates
            </p>
          </div>

          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Connection Status */}
        <div className="mt-4 flex items-center gap-2 text-sm">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              wsStatus === 'connected'
                ? 'bg-success animate-pulse'
                : wsStatus === 'connecting'
                ? 'bg-warning animate-pulse'
                : 'bg-muted-foreground'
            }`}
          />
          <span className="text-muted-foreground">
            {wsStatus === 'connected'
              ? 'Live updates active'
              : wsStatus === 'connecting'
              ? 'Connecting...'
              : 'Disconnected (using polling)'}
          </span>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load generation jobs. Please try again.
          </AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
          <p className="text-muted-foreground">Loading generation jobs...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && jobs.length === 0 && (
        <div className="text-center py-12">
          <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">No generation jobs yet</h3>
          <p className="text-muted-foreground">
            Start generating content from the Sub-Chapters page to see your generation history
          </p>
        </div>
      )}

      {/* Job Lists */}
      {!isLoading && jobs.length > 0 && (
        <div className="space-y-8">
          {/* Active Jobs */}
          {activeJobs.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-accent animate-pulse" />
                Active Jobs ({activeJobs.length})
              </h2>
              <div className="grid gap-4">
                {activeJobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onCancel={handleCancel}
                    onViewContent={handleViewContent}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Completed Jobs */}
          {completedJobs.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-4 text-green-700 flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                Completed ({completedJobs.length})
              </h2>
              <div className="grid gap-4">
                {completedJobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onViewContent={handleViewContent}
                    showActions={true}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Failed Jobs */}
          {failedJobs.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-4 text-red-700 flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
                Failed / Cancelled ({failedJobs.length})
              </h2>
              <div className="grid gap-4">
                {failedJobs.map((job) => (
                  <JobCard key={job.id} job={job} showActions={false} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
