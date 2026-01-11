/**
 * Profile/Settings page for managing user profile information.
 */

import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { updateUserProfile, createUserProfile, type UpdateUserProfileRequest } from '@/api/userProfile'
import { useAuthStore } from '@/stores/authStore'
import { ArrowLeft, User, Save, UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'

export function ProfilePage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const profile = useAuthStore((state) => state.profile)
  const refreshProfile = useAuthStore((state) => state.refreshProfile)
  const user = useAuthStore((state) => state.user)
  const initialized = useAuthStore((state) => state.initialized)

  const [formData, setFormData] = useState({
    name: '',
    bio: '',
    avatar_url: '',
  })

  useEffect(() => {
    if (profile) {
      setFormData({
        name: profile.name || '',
        bio: profile.bio || '',
        avatar_url: profile.avatar_url || '',
      })
    }
  }, [profile])

  const createMutation = useMutation({
    mutationFn: (name: string) => createUserProfile(name),
    onSuccess: async () => {
      await refreshProfile()
      toast({
        title: 'Success',
        description: 'Profile created successfully',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create profile',
        variant: 'destructive',
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: UpdateUserProfileRequest) => updateUserProfile(data),
    onSuccess: async () => {
      await refreshProfile()
      toast({
        title: 'Success',
        description: 'Profile updated successfully',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update profile',
        variant: 'destructive',
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!profile) {
      // Create profile
      createMutation.mutate(formData.name)
    } else {
      // Update profile
      updateMutation.mutate(formData)
    }
  }

  const handleChange = (field: keyof typeof formData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  if (!initialized) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Button
        variant="ghost"
        onClick={() => navigate('/dashboard')}
        className="mb-6"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Dashboard
      </Button>

      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">
          {profile ? 'Profile & Settings' : 'Create Your Profile'}
        </h1>
        <p className="text-muted-foreground">
          {profile
            ? 'Manage your personal information and preferences.'
            : 'Set up your profile to get started.'}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {profile ? <User className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            {profile ? 'Personal Information' : 'Create Profile'}
          </CardTitle>
          <CardDescription>
            {profile
              ? 'Update your profile details visible to you.'
              : 'Enter your name to create your profile.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="Your name"
                required
              />
              <p className="text-xs text-muted-foreground">
                This name will be displayed throughout the app.
              </p>
            </div>

            {profile && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={formData.bio}
                    onChange={(e) => handleChange('bio', e.target.value)}
                    placeholder="Tell us about yourself..."
                    rows={4}
                    maxLength={500}
                  />
                  <p className="text-xs text-muted-foreground">
                    {formData.bio.length}/500 characters
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="avatar_url">Avatar URL</Label>
                  <Input
                    id="avatar_url"
                    value={formData.avatar_url}
                    onChange={(e) => handleChange('avatar_url', e.target.value)}
                    placeholder="https://example.com/avatar.jpg"
                    type="url"
                  />
                  <p className="text-xs text-muted-foreground">
                    Paste a URL to an image to use as your avatar.
                  </p>
                  {formData.avatar_url && (
                    <div className="mt-3">
                      <p className="text-xs text-muted-foreground mb-2">Preview:</p>
                      <img
                        src={formData.avatar_url}
                        alt="Avatar preview"
                        className="w-24 h-24 rounded-full object-cover border"
                        onError={(e) => {
                          e.currentTarget.src = ''
                          e.currentTarget.alt = 'Invalid image URL'
                        }}
                      />
                    </div>
                  )}
                </div>
              </>
            )}

            <div className="flex gap-3 pt-4">
              <Button
                type="submit"
                disabled={
                  (profile ? updateMutation.isPending : createMutation.isPending) ||
                  !formData.name.trim()
                }
              >
                {profile ? (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4 mr-2" />
                    {createMutation.isPending ? 'Creating...' : 'Create Profile'}
                  </>
                )}
              </Button>
              {profile && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setFormData({
                      name: profile.name || '',
                      bio: profile.bio || '',
                      avatar_url: profile.avatar_url || '',
                    })
                  }}
                  disabled={updateMutation.isPending}
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Account Information (Read-only) - Only show if profile exists */}
      {profile && (
        <Card className="mt-6">
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>
            Your account details (read-only).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>User ID</Label>
            <p className="text-sm text-muted-foreground font-mono mt-1">{profile.id}</p>
          </div>
          <div>
            <Label>Account Created</Label>
            <p className="text-sm text-muted-foreground mt-1">
              {new Date(profile.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div>
            <Label>Last Updated</Label>
            <p className="text-sm text-muted-foreground mt-1">
              {new Date(profile.updated_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
        </CardContent>
      </Card>
      )}
    </div>
  )
}
