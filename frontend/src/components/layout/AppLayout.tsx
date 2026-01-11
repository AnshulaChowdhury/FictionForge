/**
 * Main application layout with header and sidebar.
 * Redesigned with generous spacing and modern aesthetics.
 */

import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from '@/components/sidebar/Sidebar'

export function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          {/* Content container - pages control their own padding for flexibility */}
          <Outlet />
        </main>
      </div>
    </div>
  )
}