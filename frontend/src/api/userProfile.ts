/**
 * API functions for user profile operations.
 */

import { apiClient } from './client'

export interface UserProfile {
  id: string
  name: string
  bio?: string | null
  avatar_url?: string | null
  created_at: string
  updated_at: string
}

export interface UpdateUserProfileRequest {
  name?: string
  bio?: string
  avatar_url?: string
}

/**
 * Get the current user's profile.
 */
export async function getUserProfile(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>('/api/profile')
  return response.data
}

/**
 * Create a new profile for the current user.
 */
export async function createUserProfile(name: string): Promise<UserProfile> {
  const response = await apiClient.post<UserProfile>('/api/profile', null, {
    params: { name },
  })
  return response.data
}

/**
 * Update the current user's profile.
 */
export async function updateUserProfile(
  data: UpdateUserProfileRequest
): Promise<UserProfile> {
  const response = await apiClient.put<UserProfile>('/api/profile', data)
  return response.data
}
