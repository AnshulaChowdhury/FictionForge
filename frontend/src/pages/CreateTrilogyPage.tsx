/**
 * Create Trilogy page with form validation.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTrilogy, type CreateTrilogyRequest } from '@/api/trilogy'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'

const createTrilogySchema = z.object({
  title: z
    .string()
    .min(1, 'Title is required')
    .max(100, 'Title must be 100 characters or less')
    .refine((val) => val.trim().length > 0, 'Title cannot be empty'),
  author: z
    .string()
    .min(1, 'Author is required')
    .max(50, 'Author must be 50 characters or less')
    .refine((val) => val.trim().length > 0, 'Author cannot be empty'),
  description: z
    .string()
    .max(2000, 'Description must be 2000 characters or less')
    .optional(),
  narrative_overview: z
    .string()
    .max(2000, 'Narrative overview must be 2000 characters or less')
    .optional(),
})

type CreateTrilogyForm = z.infer<typeof createTrilogySchema>

export function CreateTrilogyPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateTrilogyForm>({
    resolver: zodResolver(createTrilogySchema),
  })

  const createMutation = useMutation({
    mutationFn: createTrilogy,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['trilogies'] })
      navigate(`/trilogy/${data.trilogy.id}`)
    },
  })

  const onSubmit = (data: CreateTrilogyForm) => {
    const request: CreateTrilogyRequest = {
      title: data.title.trim(),
      author: data.author.trim(),
      description: data.description?.trim() || undefined,
      narrative_overview: data.narrative_overview?.trim() || undefined,
    }
    createMutation.mutate(request)
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Button
        variant="ghost"
        onClick={() => navigate('/dashboard')}
        className="mb-6"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Dashboard
      </Button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Create New Trilogy</h1>
        <p className="text-muted-foreground">
          Start your creative journey by setting up a new trilogy project with 3
          books.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardContent className="pt-6 space-y-6">
            {/* Title Field */}
            <div className="space-y-2">
              <Label htmlFor="title">
                Title <span className="text-destructive">*</span>
              </Label>
              <Input
                id="title"
                {...register('title')}
                placeholder="Enter trilogy title"
              />
              {errors.title && (
                <p className="text-sm text-destructive">
                  {errors.title.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum 100 characters
              </p>
            </div>

            {/* Author Field */}
            <div className="space-y-2">
              <Label htmlFor="author">
                Author <span className="text-destructive">*</span>
              </Label>
              <Input
                id="author"
                {...register('author')}
                placeholder="Enter author name"
              />
              {errors.author && (
                <p className="text-sm text-destructive">
                  {errors.author.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum 50 characters
              </p>
            </div>

            {/* Description Field */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                {...register('description')}
                rows={4}
                placeholder="Enter trilogy description (optional)"
              />
              {errors.description && (
                <p className="text-sm text-destructive">
                  {errors.description.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum 2000 characters
              </p>
            </div>

            {/* Narrative Overview Field */}
            <div className="space-y-2">
              <Label htmlFor="narrative_overview">Narrative Overview</Label>
              <Textarea
                id="narrative_overview"
                {...register('narrative_overview')}
                rows={6}
                placeholder="Enter high-level narrative overview for the trilogy (optional)"
              />
              {errors.narrative_overview && (
                <p className="text-sm text-destructive">
                  {errors.narrative_overview.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum 2000 characters
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Form Actions */}
        <div className="flex items-center justify-end space-x-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/dashboard')}
            disabled={createMutation.isPending}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create Trilogy'}
          </Button>
        </div>

        {/* Error Message */}
        {createMutation.isError && (
          <Alert variant="destructive">
            <AlertDescription>
              Failed to create trilogy. Please try again.
            </AlertDescription>
          </Alert>
        )}
      </form>
    </div>
  )
}
