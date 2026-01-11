/**
 * Main App component with routing configuration.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/queryClient'

// Auth pages
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'

// Protected pages
import { DashboardPage } from '@/pages/DashboardPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { CreateTrilogyPage } from '@/pages/CreateTrilogyPage'
import { TrilogyDetailPage } from '@/pages/TrilogyDetailPage'
import { WorldRulesPage } from '@/pages/WorldRulesPage'
import { RuleAnalyticsPage } from '@/pages/RuleAnalyticsPage'
import { CharactersPage } from '@/pages/CharactersPage'
import { ChaptersPage } from '@/pages/ChaptersPage'
import { SubChaptersPage } from '@/pages/SubChaptersPage'
import GenerationQueuePage from '@/pages/GenerationQueuePage'

// Layout and auth
import { AppLayout } from '@/components/layout/AppLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Toaster } from '@/components/ui/toaster'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/generation-queue" element={<GenerationQueuePage />} />
              <Route path="/trilogy/create" element={<CreateTrilogyPage />} />
              <Route path="/trilogy/:trilogyId" element={<TrilogyDetailPage />} />
              <Route path="/trilogy/:trilogyId/world-rules" element={<WorldRulesPage />} />
              <Route path="/trilogy/:trilogyId/rule-analytics" element={<RuleAnalyticsPage />} />
              <Route path="/trilogy/:trilogyId/characters" element={<CharactersPage />} />
              <Route path="/book/:bookId/chapters" element={<ChaptersPage />} />
              <Route path="/chapter/:chapterId/sub-chapters" element={<SubChaptersPage />} />
            </Route>
          </Route>

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
      <Toaster />
    </QueryClientProvider>
  )
}

export default App
