/**
 * API functions for trilogy operations.
 */

import { apiClient } from './client'

export interface CreateTrilogyRequest {
  title: string
  description?: string
  author: string
  narrative_overview?: string
}

export interface Book {
  id: string
  trilogy_id: string
  book_number: number
  title: string
  target_word_count: number
  current_word_count: number
  created_at: string
  updated_at: string
}

export interface Trilogy {
  id: string
  user_id: string
  title: string
  description?: string
  author: string
  narrative_overview?: string
  is_primary: boolean
  created_at: string
  updated_at: string
}

export interface CreateTrilogyResponse {
  trilogy: Trilogy
  books: Book[]
  message: string
}

export interface TrilogyWithBooks extends Trilogy {
  books?: Book[]
}

export interface TrilogyStats {
  trilogy: Trilogy
  total_word_count: number
  estimated_pages: number
  total_chapters: number
  chapters_completed: number
  chapters_in_progress: number
  chapters_not_started: number
  books_progress: Array<{
    book_number: number
    title: string
    completion_percentage: number
    current_word_count: number
    target_word_count: number
  }>
}

/**
 * Create a new trilogy with 3 books.
 */
export async function createTrilogy(
  data: CreateTrilogyRequest
): Promise<CreateTrilogyResponse> {
  const response = await apiClient.post<CreateTrilogyResponse>(
    '/api/trilogy/create',
    data
  )
  return response.data
}

/**
 * Get all trilogies for the current user.
 */
export async function getUserTrilogies(): Promise<Trilogy[]> {
  const response = await apiClient.get<Trilogy[]>('/api/trilogy')
  return response.data
}

/**
 * Get statistics for the active (most recently updated) trilogy.
 */
export async function getActiveTrilogyStats(): Promise<TrilogyStats> {
  const response = await apiClient.get<TrilogyStats>('/api/trilogy/active/stats')
  return response.data
}

/**
 * Get a specific trilogy by ID.
 */
export async function getTrilogy(trilogyId: string): Promise<Trilogy> {
  const response = await apiClient.get<Trilogy>(`/api/trilogy/${trilogyId}`)
  return response.data
}

/**
 * Get all books for a specific trilogy.
 */
export async function getTrilogyBooks(trilogyId: string): Promise<Book[]> {
  const response = await apiClient.get<Book[]>(`/api/trilogy/${trilogyId}/books`)
  return response.data
}

/**
 * Get a single book by ID (helper function for chapter management).
 */
export async function getBook(bookId: string): Promise<Book> {
  // Books don't have a dedicated endpoint, so we'll need to fetch from parent trilogy
  // This is a temporary implementation - ideally there would be GET /api/books/:bookId
  const response = await apiClient.get<Book>(`/api/books/${bookId}`)
  return response.data
}

/**
 * Update a book's title.
 */
export async function updateBook(
  bookId: string,
  data: { title: string }
): Promise<Book> {
  const response = await apiClient.put<Book>(`/api/books/${bookId}`, data)
  return response.data
}

/**
 * Update a trilogy's metadata.
 */
export async function updateTrilogy(
  trilogyId: string,
  data: {
    title?: string
    description?: string
    author?: string
    narrative_overview?: string
  }
): Promise<Trilogy> {
  const response = await apiClient.put<Trilogy>(
    `/api/trilogy/${trilogyId}`,
    data
  )
  return response.data
}

/**
 * Delete a trilogy and all associated data.
 * This action cannot be undone.
 */
export async function deleteTrilogy(trilogyId: string): Promise<void> {
  await apiClient.delete(`/api/trilogy/${trilogyId}`)
}

/**
 * Set a trilogy as the user's primary trilogy.
 * Automatically unsets any other primary trilogy.
 */
export async function setPrimaryTrilogy(trilogyId: string): Promise<Trilogy> {
  const response = await apiClient.patch<Trilogy>(
    `/api/trilogy/${trilogyId}/set-primary`
  )
  return response.data
}

/**
 * Unset a trilogy as the user's primary trilogy.
 * After this, no trilogy will be marked as primary.
 */
export async function unsetPrimaryTrilogy(trilogyId: string): Promise<Trilogy> {
  const response = await apiClient.patch<Trilogy>(
    `/api/trilogy/${trilogyId}/unset-primary`
  )
  return response.data
}
