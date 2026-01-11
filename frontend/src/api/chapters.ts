/**
 * API functions for chapter operations (Epic 4).
 */

import { apiClient } from './client'

export interface Chapter {
  id: string
  book_id: string
  character_id: string
  title: string
  chapter_number: number
  chapter_plot?: string
  target_word_count?: number
  current_word_count: number
  created_at: string
  updated_at: string
}

export interface CreateChapterRequest {
  book_id: string
  character_id: string
  title: string
  chapter_plot?: string
  target_word_count?: number
}

export interface UpdateChapterRequest {
  title?: string
  chapter_plot?: string
  character_id?: string
  target_word_count?: number
}

export interface ChapterReorderRequest {
  new_position: number
}

export interface ChapterListResponse {
  chapters: Chapter[]
  total: number
}

export interface ChapterProgressResponse {
  chapter_id: string
  title: string
  target_word_count?: number
  current_word_count: number
  percentage: number
  status: 'not_started' | 'in_progress' | 'complete' | 'over_target'
}

export interface BookProgressResponse {
  book_id: string
  total_chapters: number
  chapters_completed: number
  total_target_word_count: number
  total_current_word_count: number
  overall_percentage: number
  chapters_by_status: {
    not_started: number
    in_progress: number
    complete: number
    over_target: number
  }
}

export interface ChapterDeleteResponse {
  id: string
  message: string
}

/**
 * Create a new chapter.
 */
export async function createChapter(
  data: CreateChapterRequest
): Promise<Chapter> {
  const response = await apiClient.post<Chapter>('/api/chapters', data)
  return response.data
}

/**
 * Get all chapters for a book.
 */
export async function getBookChapters(
  bookId: string
): Promise<ChapterListResponse> {
  const response = await apiClient.get<ChapterListResponse>(
    `/api/chapters/book/${bookId}`
  )
  return response.data
}

/**
 * Get a specific chapter by ID.
 */
export async function getChapter(chapterId: string): Promise<Chapter> {
  const response = await apiClient.get<Chapter>(`/api/chapters/${chapterId}`)
  return response.data
}

/**
 * Update a chapter.
 */
export async function updateChapter(
  chapterId: string,
  data: UpdateChapterRequest
): Promise<Chapter> {
  const response = await apiClient.put<Chapter>(
    `/api/chapters/${chapterId}`,
    data
  )
  return response.data
}

/**
 * Delete a chapter.
 */
export async function deleteChapter(
  chapterId: string
): Promise<ChapterDeleteResponse> {
  const response = await apiClient.delete<ChapterDeleteResponse>(
    `/api/chapters/${chapterId}`
  )
  return response.data
}

/**
 * Reorder a chapter to a new position.
 */
export async function reorderChapter(
  chapterId: string,
  newPosition: number
): Promise<ChapterListResponse> {
  const response = await apiClient.post<ChapterListResponse>(
    `/api/chapters/${chapterId}/reorder`,
    { new_position: newPosition }
  )
  return response.data
}

/**
 * Get chapter progress.
 */
export async function getChapterProgress(
  chapterId: string
): Promise<ChapterProgressResponse> {
  const response = await apiClient.get<ChapterProgressResponse>(
    `/api/chapters/${chapterId}/progress`
  )
  return response.data
}

/**
 * Get book progress summary.
 */
export async function getBookProgress(
  bookId: string
): Promise<BookProgressResponse> {
  const response = await apiClient.get<BookProgressResponse>(
    `/api/chapters/book/${bookId}/progress`
  )
  return response.data
}
