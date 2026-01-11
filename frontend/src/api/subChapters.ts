/**
 * API functions for sub-chapter operations (Epic 6).
 */

import { apiClient } from './client'

export interface SubChapter {
  id: string
  chapter_id: string
  character_id: string
  sub_chapter_number: number
  title?: string
  plot_points?: string
  content?: string
  word_count: number
  status: 'draft' | 'in_progress' | 'completed' | 'needs_review'
  current_version_id?: string
  generation_job_id?: string  // Epic 10: Job ID for tracking generation progress
  created_at: string
  updated_at: string
}

export interface SubChapterWithProgress extends SubChapter {
  progress_percentage: number
  progress_status: 'not_started' | 'in_progress' | 'near_complete' | 'complete'
  over_target: boolean
}

export interface CreateSubChapterRequest {
  chapter_id: string
  title?: string
  plot_points?: string
}

export interface UpdateSubChapterRequest {
  title?: string
  plot_points?: string
  status?: 'draft' | 'in_progress' | 'completed' | 'needs_review'
}

export interface UpdateSubChapterContentRequest {
  content: string
  change_description?: string
}

export interface SubChapterCreateResponse {
  sub_chapter_id: string
  generation_job_id?: string
  status: string
  websocket_url?: string
}

export interface SubChapterReorderRequest {
  new_position: number
}

export interface SubChapterProgress {
  sub_chapter_id: string
  word_count: number
  target_word_count: number
  progress_percentage: number
  status: string
}

export interface ChapterProgress {
  chapter_id: string
  total_sub_chapters: number
  sub_chapters_completed: number
  total_word_count: number
  total_target_word_count: number
  overall_percentage: number
  sub_chapters_by_status: {
    draft: number
    in_progress: number
    completed: number
    needs_review: number
  }
}

export interface SubChapterRegenerateRequest {
  plot_points?: string
  character_id?: string
}

export interface RegenerateResponse {
  job_id: string
  sub_chapter_id: string
  websocket_url: string
}

export interface BulkRegenerateResponse {
  job_ids: string[]
  chapter_id: string
  websocket_url: string
}

export interface ContentReviewFlag {
  id: string
  sub_chapter_id: string
  flag_type: 'plot_point_changed' | 'character_inconsistency' | 'manual_review'
  description: string
  old_value?: string
  new_value?: string
  created_at: string
  resolved_at?: string
  resolved_by_user_id?: string
}

export interface ContentReviewFlagResolve {
  resolution_notes?: string
}

export interface SubChapterVersionListItem {
  id: string
  version_number: number
  word_count: number
  change_description?: string
  is_ai_generated: boolean
  created_at: string
  is_current: boolean
}

export interface SubChapterVersion {
  id: string
  sub_chapter_id: string
  version_number: number
  content: string
  word_count: number
  change_description?: string
  snapshot_metadata?: Record<string, any>
  generated_by_model?: string
  generation_job_id?: string
  is_ai_generated: boolean
  created_at: string
  created_by_user_id?: string
  is_current: boolean
  updated_at?: string
}

export interface UpdateVersionDescriptionRequest {
  change_description: string
}

/**
 * Create a new sub-chapter.
 */
export async function createSubChapter(
  data: CreateSubChapterRequest
): Promise<SubChapterCreateResponse> {
  const response = await apiClient.post<SubChapterCreateResponse>(
    '/api/sub-chapters',
    data
  )
  return response.data
}

/**
 * Get a single sub-chapter by ID.
 */
export async function getSubChapter(
  subChapterId: string
): Promise<SubChapter> {
  const response = await apiClient.get<SubChapter>(
    `/api/sub-chapters/${subChapterId}`
  )
  return response.data
}

/**
 * Get all sub-chapters for a chapter.
 */
export async function getChapterSubChapters(
  chapterId: string
): Promise<SubChapter[]> {
  const response = await apiClient.get<SubChapter[]>(
    `/api/sub-chapters/chapter/${chapterId}`
  )
  return response.data
}

/**
 * Update a sub-chapter.
 */
export async function updateSubChapter(
  subChapterId: string,
  data: UpdateSubChapterRequest
): Promise<SubChapter> {
  const response = await apiClient.put<SubChapter>(
    `/api/sub-chapters/${subChapterId}`,
    data
  )
  return response.data
}

/**
 * Update sub-chapter content and create a new version.
 */
export async function updateSubChapterContent(
  subChapterId: string,
  data: UpdateSubChapterContentRequest
): Promise<SubChapter> {
  const response = await apiClient.put<SubChapter>(
    `/api/sub-chapters/${subChapterId}/content`,
    data
  )
  return response.data
}

/**
 * Delete a sub-chapter.
 */
export async function deleteSubChapter(subChapterId: string): Promise<void> {
  await apiClient.delete(`/api/sub-chapters/${subChapterId}`)
}

/**
 * Update plot points (with automatic content review flagging).
 */
export async function updatePlotPoints(
  subChapterId: string,
  plotPoints: string
): Promise<SubChapter> {
  const response = await apiClient.put<SubChapter>(
    `/api/sub-chapters/${subChapterId}/plot-points`,
    { plot_points: plotPoints }
  )
  return response.data
}

/**
 * Get content review flags for a sub-chapter.
 */
export async function getContentReviewFlags(
  subChapterId: string
): Promise<ContentReviewFlag[]> {
  const response = await apiClient.get<ContentReviewFlag[]>(
    `/api/sub-chapters/${subChapterId}/flags`
  )
  return response.data
}

/**
 * Resolve a content review flag.
 */
export async function resolveContentReviewFlag(
  flagId: string,
  data: ContentReviewFlagResolve
): Promise<void> {
  await apiClient.post(`/api/sub-chapters/flags/${flagId}/resolve`, data)
}

/**
 * Reorder a sub-chapter to a new position.
 */
export async function reorderSubChapter(
  subChapterId: string,
  newPosition: number
): Promise<SubChapter[]> {
  const response = await apiClient.post<SubChapter[]>(
    `/api/sub-chapters/${subChapterId}/reorder`,
    { new_position: newPosition }
  )
  return response.data
}

/**
 * Move a sub-chapter up one position.
 */
export async function moveSubChapterUp(
  subChapterId: string
): Promise<SubChapter[]> {
  const response = await apiClient.post<SubChapter[]>(
    `/api/sub-chapters/${subChapterId}/move-up`
  )
  return response.data
}

/**
 * Move a sub-chapter down one position.
 */
export async function moveSubChapterDown(
  subChapterId: string
): Promise<SubChapter[]> {
  const response = await apiClient.post<SubChapter[]>(
    `/api/sub-chapters/${subChapterId}/move-down`
  )
  return response.data
}

/**
 * Get progress for a single sub-chapter.
 */
export async function getSubChapterProgress(
  subChapterId: string
): Promise<SubChapterProgress> {
  const response = await apiClient.get<SubChapterProgress>(
    `/api/sub-chapters/${subChapterId}/progress`
  )
  return response.data
}

/**
 * Get progress for all sub-chapters in a chapter.
 */
export async function getChapterProgress(
  chapterId: string
): Promise<ChapterProgress> {
  const response = await apiClient.get<ChapterProgress>(
    `/api/sub-chapters/chapter/${chapterId}/progress`
  )
  return response.data
}

/**
 * Regenerate content for a sub-chapter.
 */
export async function regenerateSubChapter(
  subChapterId: string,
  data: SubChapterRegenerateRequest
): Promise<RegenerateResponse> {
  const response = await apiClient.post<RegenerateResponse>(
    `/api/sub-chapters/${subChapterId}/regenerate`,
    data
  )
  return response.data
}

/**
 * Regenerate all sub-chapters in a chapter.
 */
export async function regenerateChapterSubChapters(
  chapterId: string
): Promise<BulkRegenerateResponse> {
  const response = await apiClient.post<BulkRegenerateResponse>(
    `/api/sub-chapters/chapter/${chapterId}/regenerate`
  )
  return response.data
}

/**
 * Get version history for a sub-chapter.
 */
export async function getSubChapterVersions(
  subChapterId: string
): Promise<SubChapterVersionListItem[]> {
  const response = await apiClient.get<SubChapterVersionListItem[]>(
    `/api/sub-chapters/${subChapterId}/versions`
  )
  return response.data
}

/**
 * Get a specific version.
 */
export async function getSubChapterVersion(
  versionId: string
): Promise<SubChapterVersion> {
  const response = await apiClient.get<SubChapterVersion>(
    `/api/sub-chapters/versions/${versionId}`
  )
  return response.data
}

/**
 * Restore a previous version.
 */
export async function restoreSubChapterVersion(
  versionId: string
): Promise<SubChapter> {
  const response = await apiClient.post<SubChapter>(
    `/api/sub-chapters/versions/${versionId}/restore`
  )
  return response.data
}

/**
 * Update the description for a specific version.
 * Epic 7 Story 3: Document reasoning behind content changes.
 */
export async function updateVersionDescription(
  versionId: string,
  changeDescription: string
): Promise<SubChapterVersion> {
  const response = await apiClient.put<SubChapterVersion>(
    `/api/sub-chapters/versions/${versionId}/description`,
    { change_description: changeDescription }
  )
  return response.data
}
