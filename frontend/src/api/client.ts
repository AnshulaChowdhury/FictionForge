/**
 * API client for backend communication.
 * Automatically includes auth token in requests when available.
 */

import axios from 'axios'
import { supabase } from '@/lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

if (!API_BASE_URL) {
  throw new Error('Missing VITE_API_BASE_URL environment variable')
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for all requests
})

// Add auth token to requests automatically
apiClient.interceptors.request.use(async (config) => {
  try {
    // Add timeout to prevent hanging on slow Supabase calls
    const sessionPromise = supabase.auth.getSession()
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Auth session check timed out')), 5000)
    )

    const {
      data: { session },
    } = await Promise.race([sessionPromise, timeoutPromise]) as any

    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
  } catch (error) {
    // If session check fails/times out, continue without auth token
    // (will get 401 if auth is required)
    console.warn('Failed to get session for request:', error)
  }

  return config
})

// Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle timeout errors
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      console.error('Request timeout:', error)
      error.message = 'Request timed out. Please try again.'
    }

    // Handle 401 errors by redirecting to login
    if (error.response?.status === 401) {
      // Clear session and redirect to login
      supabase.auth.signOut()
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)
