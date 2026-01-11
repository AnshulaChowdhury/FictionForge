/**
 * API functions for character operations (Epic 2).
 */

import { apiClient } from './client'

export type Gender =
  | 'cisgender_male'
  | 'cisgender_female'
  | 'transgender_male'
  | 'transgender_female'
  | 'nonbinary'

export const GENDER_LABELS: Record<Gender, string> = {
  cisgender_male: 'Cisgender Male',
  cisgender_female: 'Cisgender Female',
  transgender_male: 'Transgender Male',
  transgender_female: 'Transgender Female',
  nonbinary: 'Non-binary',
}

export interface CharacterTraits {
  personality?: string[]
  speech_patterns?: string[]
  physical_description?: string
  background?: string
  motivations?: string[]
}

export interface Character {
  id: string
  trilogy_id: string
  name: string
  gender?: Gender
  description?: string
  traits?: CharacterTraits
  character_arc?: string
  book_ids: string[]
  created_at: string
  updated_at: string
}

export interface CreateCharacterRequest {
  trilogy_id: string
  name: string
  gender?: Gender
  description?: string
  traits?: CharacterTraits
  character_arc?: string
  book_ids?: string[]
}

export interface UpdateCharacterRequest {
  name?: string
  gender?: Gender
  description?: string
  traits?: CharacterTraits
  character_arc?: string
  book_ids?: string[]
}

export interface CharacterListResponse {
  characters: Character[]
  total: number
}

export interface CharacterDeleteResponse {
  id: string
  message: string
}

/**
 * Create a new character.
 */
export async function createCharacter(
  data: CreateCharacterRequest
): Promise<Character> {
  const response = await apiClient.post<Character>('/api/characters', data)
  return response.data
}

/**
 * Get all characters for a trilogy.
 */
export async function getTrilogyCharacters(
  trilogyId: string
): Promise<CharacterListResponse> {
  const response = await apiClient.get<CharacterListResponse>(
    `/api/characters/trilogy/${trilogyId}`
  )
  return response.data
}

/**
 * Get a specific character by ID.
 */
export async function getCharacter(characterId: string): Promise<Character> {
  const response = await apiClient.get<Character>(`/api/characters/${characterId}`)
  return response.data
}

/**
 * Update a character.
 */
export async function updateCharacter(
  characterId: string,
  data: UpdateCharacterRequest
): Promise<Character> {
  const response = await apiClient.put<Character>(
    `/api/characters/${characterId}`,
    data
  )
  return response.data
}

/**
 * Delete a character.
 */
export async function deleteCharacter(
  characterId: string
): Promise<CharacterDeleteResponse> {
  const response = await apiClient.delete<CharacterDeleteResponse>(
    `/api/characters/${characterId}`
  )
  return response.data
}
