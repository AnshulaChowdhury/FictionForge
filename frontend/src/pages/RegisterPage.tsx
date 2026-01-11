/**
 * Registration page with Supabase Auth UI.
 */

import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '@/lib/supabase'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function RegisterPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (user) {
      navigate('/dashboard')
    }
  }, [user, navigate])

  // Listen for auth state changes to show confirmation message
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('Auth event:', event, session)

      // Check for initial session (user confirmed email via link)
      if (event === 'INITIAL_SESSION' && session) {
        navigate('/dashboard')
      }
      // User signed in successfully
      else if (event === 'SIGNED_IN' && session) {
        navigate('/dashboard')
      }
      // Password recovery or email change
      else if (event === 'PASSWORD_RECOVERY' || event === 'USER_UPDATED') {
        if (session?.user) {
          navigate('/dashboard')
        }
      }
    })

    // Check for error in URL (email confirmation error)
    const params = new URLSearchParams(window.location.search)
    if (params.get('error')) {
      setMessage({
        type: 'error',
        text: params.get('error_description') || 'An error occurred during registration.'
      })
    }
    // Check for success message (after email confirmation)
    if (params.get('type') === 'signup' || params.get('message')) {
      setMessage({
        type: 'success',
        text: 'Registration successful! Please check your email to confirm your account before signing in.'
      })
    }

    return () => subscription.unsubscribe()
  }, [navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold mb-2">Create Your Account</h1>
          <p className="text-muted-foreground">
            Join FictionForge.ai to start writing
          </p>
        </div>

        {message && (
          <div className={`mb-4 p-4 rounded-lg border ${
            message.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <p className="text-sm font-medium">{message.text}</p>
          </div>
        )}

        <div className="bg-card p-8 rounded-lg shadow-lg border border-border">
          <Auth
            supabaseClient={supabase}
            appearance={{ theme: ThemeSupa }}
            theme="light"
            providers={[]}
            redirectTo={window.location.origin + '/dashboard'}
            view="sign_up"
            showLinks={false}
          />
        </div>

        <div className="mt-4 text-center text-sm text-muted-foreground">
          <p>
            Already have an account?{' '}
            <a href="/login" className="text-primary hover:underline">
              Sign in here
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
