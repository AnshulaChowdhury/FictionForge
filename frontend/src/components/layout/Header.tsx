/**
 * Header component with user menu, theme picker, and navigation.
 * Minimalist design with clean typography.
 */

import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { LogOut, Feather, User, ChevronDown } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { ThemePicker } from '@/components/ui/theme-picker'

export function Header() {
  const { user, profile, signOut } = useAuthStore()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  const getInitials = () => {
    if (profile?.name) {
      const parts = profile.name.split(' ')
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      }
      return profile.name.substring(0, 2).toUpperCase()
    }
    return user?.email?.charAt(0).toUpperCase() || '?'
  }

  const displayName = profile?.name || user?.email?.split('@')[0] || 'User'

  return (
    <header className="bg-background/95 backdrop-blur-sm border-b border-border/50 sticky top-0 z-50">
      <div className="max-w-screen-2xl mx-auto px-6 h-12 flex items-center justify-between">
        {/* Logo */}
        <div
          className="flex items-center gap-2 cursor-pointer group"
          onClick={() => navigate('/dashboard')}
        >
          <div className="flex items-center justify-center w-7 h-7 rounded bg-primary/90 group-hover:bg-primary transition-colors">
            <Feather className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="text-sm font-semibold text-foreground">
            FictionForge
          </span>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-1">
          <ThemePicker />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 gap-2 text-muted-foreground hover:text-foreground"
              >
                {profile?.avatar_url ? (
                  <img
                    src={profile.avatar_url}
                    alt={displayName}
                    className="w-6 h-6 rounded-full object-cover"
                  />
                ) : (
                  <div className="flex items-center justify-center w-6 h-6 rounded-full bg-muted text-xs font-medium">
                    {getInitials()}
                  </div>
                )}
                <span className="hidden sm:inline text-xs font-medium">
                  {displayName}
                </span>
                <ChevronDown className="w-3 h-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <div className="px-2 py-1.5 border-b border-border mb-1">
                <p className="text-sm font-medium truncate">{displayName}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
              <DropdownMenuItem
                onClick={() => navigate('/profile')}
                className="cursor-pointer text-sm"
              >
                <User className="w-3.5 h-3.5 mr-2" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleSignOut}
                className="text-destructive focus:text-destructive cursor-pointer text-sm"
              >
                <LogOut className="w-3.5 h-3.5 mr-2" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
