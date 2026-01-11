/**
 * Generation Jobs API Client (Epic 10)
 *
 * Provides functions for:
 * - Fetching active generation jobs
 * - Polling job status (202/200 pattern)
 * - Cancelling jobs
 * - Managing notification preferences
 * - Checking character vector store status
 */

import { apiClient } from './client'

// ============================================================================
// Types
// ============================================================================

export interface GenerationJob {
  id: string
  user_id: string
  trilogy_id: string
  sub_chapter_id: string
  arq_job_id: string | null
  status: 'queued' | 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  job_type: string | null
  priority: number
  stage: string | null
  progress_percentage: number
  estimated_completion: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  updated_at: string | null
  error_message: string | null
  retry_count: number
  word_count: number | null
  version_id: string | null
  version_number: number | null
  model_used: string | null
  result_metadata: Record<string, any> | null
  generation_params: Record<string, any> | null
  can_cancel: boolean
  time_remaining_seconds: number | null
}

export interface GenerationJobListItem {
  id: string
  trilogy_id: string
  sub_chapter_id: string
  chapter_id: string | null
  sub_chapter_title: string | null
  chapter_title: string | null
  character_name: string | null
  status: string
  stage: string | null
  progress_percentage: number
  estimated_completion: string | null
  created_at: string
  started_at: string | null
  word_count: number | null
  can_cancel: boolean
  time_remaining_seconds: number | null
  queue_position: number | null
}

export interface GenerationJobListResponse {
  jobs: GenerationJobListItem[]
  total_count: number
  cached: boolean
  cache_ttl_seconds: number | null
}

export interface GenerationJobStatusResponse {
  job_id: string
  status: string
  stage: string | null
  progress_percentage: number
  estimated_completion: string | null
  poll_after_seconds: number | null
  message: string | null
  result: {
    sub_chapter_id: string
    word_count: number
    version_id: string | null
    version_number: number | null
  } | null
  completed_at: string | null
}

export interface CancelJobResponse {
  job_id: string
  status: string
  cancelled_at: string
  message: string
}

export interface NotificationPreferences {
  user_id: string
  email_notifications_enabled: boolean
  toast_notifications_enabled: boolean
  notification_email: string | null
  notify_on_success: boolean
  notify_on_failure: boolean
  notify_on_long_tasks: boolean
  created_at: string | null
  updated_at: string | null
}

export interface NotificationPreferencesUpdate {
  email_notifications_enabled?: boolean
  toast_notifications_enabled?: boolean
  notification_email?: string | null
  notify_on_success?: boolean
  notify_on_failure?: boolean
  notify_on_long_tasks?: boolean
}

export interface CharacterVectorStoreStatus {
  character_id: string
  status: 'not_initialized' | 'initializing' | 'ready' | 'updating' | 'failed'
  collection_name: string | null
  embedding_count: number | null
  can_generate: boolean
  initialized_at: string | null
  error_message: string | null
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get active generation jobs for current user
 */
export async function getGenerationJobs(
  status?: string,
  limit: number = 50
): Promise<GenerationJobListResponse> {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  params.append('limit', limit.toString())

  const response = await apiClient.get<GenerationJobListResponse>(
    `/api/generation-jobs?${params.toString()}`
  )
  return response.data
}

/**
 * Get a specific generation job by ID
 */
export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  const response = await apiClient.get<GenerationJob>(`/api/generation-jobs/${jobId}`)
  return response.data
}

/**
 * Poll job status (202 Accepted pattern for long-running tasks)
 *
 * Returns:
 * - HTTP 202: Job still in progress (continue polling)
 * - HTTP 200: Job completed successfully
 * - HTTP 500: Job failed
 * - HTTP 409: Job cancelled
 */
export async function getJobStatus(jobId: string): Promise<{
  status: number
  data: GenerationJobStatusResponse
}> {
  try {
    const response = await apiClient.get<GenerationJobStatusResponse>(
      `/api/generation-jobs/${jobId}/status`,
      {
        validateStatus: (status) => status < 600, // Don't throw on 4xx/5xx
      }
    )
    return {
      status: response.status,
      data: response.data,
    }
  } catch (error) {
    throw error
  }
}

/**
 * Cancel a pending or in-progress job
 */
export async function cancelJob(jobId: string): Promise<CancelJobResponse> {
  const response = await apiClient.post<CancelJobResponse>(
    `/api/generation-jobs/${jobId}/cancel`
  )
  return response.data
}

/**
 * Get user's notification preferences
 */
export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const response = await apiClient.get<NotificationPreferences>(
    '/api/generation-jobs/preferences/notifications'
  )
  return response.data
}

/**
 * Update user's notification preferences
 */
export async function updateNotificationPreferences(
  preferences: NotificationPreferencesUpdate
): Promise<NotificationPreferences> {
  const response = await apiClient.put<NotificationPreferences>(
    '/api/generation-jobs/preferences/notifications',
    preferences
  )
  return response.data
}

/**
 * Get character vector store initialization status
 */
export async function getCharacterVectorStatus(
  characterId: string
): Promise<CharacterVectorStoreStatus> {
  const response = await apiClient.get<CharacterVectorStoreStatus>(
    `/api/generation-jobs/characters/${characterId}/vector-status`
  )
  return response.data
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format time remaining for display
 */
export function formatTimeRemaining(seconds: number | null): string {
  if (!seconds || seconds <= 0) return 'Just now'

  if (seconds < 60) return `${Math.ceil(seconds)}s remaining`

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.ceil(seconds % 60)

  if (minutes < 60) {
    if (remainingSeconds > 0) {
      return `${minutes}m ${remainingSeconds}s remaining`
    }
    return `${minutes}m remaining`
  }

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}m remaining`
}

/**
 * Get status badge color
 */
export function getStatusColor(status: string): 'default' | 'success' | 'warning' | 'error' {
  switch (status) {
    case 'completed':
      return 'success'
    case 'in_progress':
    case 'queued':
    case 'pending':
      return 'default'
    case 'failed':
      return 'error'
    case 'cancelled':
      return 'warning'
    default:
      return 'default'
  }
}

/**
 * Get WebSocket URL for real-time updates
 */
export function getWebSocketUrl(token: string): string {
  const wsBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace('http', 'ws') || ''
  return `${wsBaseUrl}/api/generation-jobs/ws?token=${token}`
}
