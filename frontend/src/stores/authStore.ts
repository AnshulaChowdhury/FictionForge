/**
 * Auth store using Zustand for managing authentication state.
 */

import { create } from 'zustand'
import type { User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { getUserProfile, type UserProfile } from '@/api/userProfile'

type Session = Awaited<ReturnType<typeof supabase.auth.getSession>>['data']['session']

interface AuthState {
  user: User | null
  profile: UserProfile | null
  session: Session
  loading: boolean
  initialized: boolean
  setUser: (user: User | null) => void
  setProfile: (profile: UserProfile | null) => void
  setSession: (session: Session) => void
  setLoading: (loading: boolean) => void
  setInitialized: (initialized: boolean) => void
  signOut: () => Promise<void>
  initialize: () => Promise<void>
  refreshProfile: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  profile: null,
  session: null,
  loading: true,
  initialized: false,

  setUser: (user) => set({ user }),
  setProfile: (profile) => set({ profile }),
  setSession: (session) => set({ session }),
  setLoading: (loading) => set({ loading }),
  setInitialized: (initialized) => set({ initialized }),

  signOut: async () => {
    await supabase.auth.signOut()
    set({ user: null, profile: null, session: null })
  },

  refreshProfile: async () => {
    try {
      const profile = await getUserProfile()
      set({ profile })
    } catch (error: any) {
      // Profile might not exist yet (404), that's ok
      if (error?.response?.status !== 404) {
        console.error('Error fetching profile:', error)
      }
      set({ profile: null })
    }
  },

  initialize: async () => {
    set({ loading: true })
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      set({
        session,
        user: session?.user ?? null,
        loading: false,
        initialized: true,
      })

      // Fetch user profile if authenticated
      if (session?.user) {
        try {
          const profile = await getUserProfile()
          set({ profile })
        } catch (error: any) {
          // Profile might not exist yet (404), that's ok
          if (error?.response?.status !== 404) {
            console.error('Error fetching profile:', error)
          }
          set({ profile: null })
        }
      }

      // Listen for auth changes
      supabase.auth.onAuthStateChange(async (_event, session) => {
        set({
          session,
          user: session?.user ?? null,
        })

        // Fetch profile on sign in
        if (session?.user) {
          try {
            const profile = await getUserProfile()
            set({ profile })
          } catch (error: any) {
            // Profile might not exist yet (404), that's ok
            if (error?.response?.status !== 404) {
              console.error('Error fetching profile:', error)
            }
            set({ profile: null })
          }
        } else {
          set({ profile: null })
        }
      })
    } catch (error) {
      console.error('Error initializing auth:', error)
      set({ loading: false, initialized: true })
    }
  },
}))
