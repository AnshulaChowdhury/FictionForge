/**
 * Login page with Supabase Auth UI.
 * Redesigned with theme-aware styling and animations.
 */

import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '@/lib/supabase'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { Feather } from 'lucide-react'

export function LoginPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const theme = useThemeStore((state) => state.theme)
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null)

  useEffect(() => {
    if (user) {
      navigate('/dashboard')
    }
  }, [user, navigate])

  // Listen for auth state changes
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('Auth event:', event, session)

      if (event === 'SIGNED_IN' && session) {
        navigate('/dashboard')
      }
    })

    // Check URL parameters for messages
    const params = new URLSearchParams(window.location.search)

    // Email confirmation success
    if (params.get('type') === 'email_confirmation') {
      setMessage({
        type: 'success',
        text: 'Email confirmed! You can now sign in.'
      })
    }

    // Error messages
    if (params.get('error')) {
      const errorDesc = params.get('error_description')
      if (errorDesc === 'Email not confirmed') {
        setMessage({
          type: 'error',
          text: 'Please confirm your email address before signing in. Check your inbox for the confirmation link.'
        })
      } else {
        setMessage({
          type: 'error',
          text: errorDesc || 'An error occurred. Please try again.'
        })
      }
    }

    return () => subscription.unsubscribe()
  }, [navigate])

  // Determine if dark mode for Supabase Auth UI
  const isDark = theme === 'night-writer'

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md animate-fade-up">
        {/* Logo and branding */}
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center mb-4">
            <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary shadow-medium animate-float">
              <Feather className="w-7 h-7 text-primary-foreground" />
            </div>
          </div>
          <h1 className="text-3xl font-bold mb-2 text-primary-color">FictionForge</h1>
          <p className="text-muted-foreground">
            Sign in to start creating your story
          </p>
        </div>

        {/* Message alerts */}
        {message && (
          <div className={`mb-4 p-4 rounded-lg border animate-fade-up ${
            message.type === 'success'
              ? 'bg-success/10 border-success/20 text-success'
              : message.type === 'error'
              ? 'bg-destructive/10 border-destructive/20 text-destructive'
              : 'bg-accent/10 border-accent/20 text-accent'
          }`}>
            <p className="text-sm font-medium">{message.text}</p>
          </div>
        )}

        {/* Auth card */}
        <div className="bg-card p-8 rounded-xl shadow-medium border border-border animate-scale-in">
          <Auth
            supabaseClient={supabase}
            appearance={{
              theme: ThemeSupa,
              variables: {
                default: {
                  colors: {
                    brand: 'hsl(var(--accent))',
                    brandAccent: 'hsl(var(--accent))',
                    inputBackground: 'hsl(var(--background))',
                    inputText: 'hsl(var(--foreground))',
                    inputBorder: 'hsl(var(--border))',
                    inputBorderFocus: 'hsl(var(--accent))',
                    inputBorderHover: 'hsl(var(--border))',
                  },
                  borderWidths: {
                    buttonBorderWidth: '1px',
                    inputBorderWidth: '1px',
                  },
                  radii: {
                    borderRadiusButton: '0.5rem',
                    buttonBorderRadius: '0.5rem',
                    inputBorderRadius: '0.5rem',
                  },
                },
              },
              className: {
                button: 'transition-smooth press-effect',
                input: 'transition-fast',
                label: 'text-sm font-medium text-primary-color',
                anchor: 'text-accent hover:text-accent/80 transition-fast',
              },
            }}
            theme={isDark ? 'dark' : 'light'}
            providers={[]}
            redirectTo={window.location.origin + '/dashboard'}
            view="sign_in"
            showLinks={true}
          />
        </div>

        {/* Register link */}
        <div className="mt-6 text-center text-sm text-muted-foreground animate-fade-up" style={{ animationDelay: '200ms' }}>
          <p>
            Don't have an account?{' '}
            <a href="/register" className="text-accent hover:text-accent/80 font-medium transition-fast">
              Register here
            </a>
          </p>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-muted-foreground/60 animate-fade-up" style={{ animationDelay: '300ms' }}>
          <p>Your creative writing companion</p>
        </div>
      </div>
    </div>
  )
}
