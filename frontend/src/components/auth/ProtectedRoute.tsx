/**
 * Protected route component that requires authentication.
 * Redirects to login if user is not authenticated.
 */

import { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function ProtectedRoute() {
  const { user, loading, initialized, initialize } = useAuthStore()

  useEffect(() => {
    if (!initialized) {
      initialize()
    }
  }, [initialized, initialize])

  if (loading || !initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
