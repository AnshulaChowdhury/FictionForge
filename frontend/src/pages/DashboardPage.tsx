/**
 * Dashboard page showing welcome message and list of trilogies.
 * Minimalist design with chapter/subchapter stats per trilogy.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query'
import { getUserTrilogies, deleteTrilogy, updateTrilogy, getTrilogyBooks } from '@/api/trilogy'
import { getBookProgress } from '@/api/chapters'
import { useNavigate } from 'react-router-dom'
import { Plus, BookOpen, Calendar, Trash2, ArrowRight, Pencil, Check, X } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/hooks/use-toast'

export function DashboardPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const profile = useAuthStore((state) => state.profile)
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [trilogyToDelete, setTrilogyToDelete] = useState<{ id: string; title: string } | null>(null)
  const [editingTrilogyId, setEditingTrilogyId] = useState<string | null>(null)
  const [editedTrilogyTitle, setEditedTrilogyTitle] = useState('')

  const { data: trilogies, isLoading } = useQuery({
    queryKey: ['trilogies'],
    queryFn: getUserTrilogies,
  })

  // Fetch books for all trilogies
  const trilogyBooksQueries = useQueries({
    queries: (trilogies || []).map((trilogy) => ({
      queryKey: ['trilogyBooks', trilogy.id],
      queryFn: () => getTrilogyBooks(trilogy.id),
      enabled: !!trilogy.id,
    })),
  })

  // Create a map of trilogy id to books
  const trilogyBooksMap = new Map(
    trilogyBooksQueries
      .filter((q) => q.data)
      .map((q, index) => [trilogies?.[index]?.id, q.data])
  )

  // Fetch book progress for all books across all trilogies
  const allBooks = trilogyBooksQueries.flatMap((q) => q.data || [])
  const bookProgressQueries = useQueries({
    queries: allBooks.map((book) => ({
      queryKey: ['bookProgress', book.id],
      queryFn: () => getBookProgress(book.id),
      enabled: !!book.id,
    })),
  })

  // Create a map of book id to progress
  const bookProgressMap = new Map(
    bookProgressQueries
      .filter((q) => q.data)
      .map((q) => [q.data!.book_id, q.data!])
  )

  // Helper to get trilogy stats
  const getTrilogyChapterStats = (trilogyId: string) => {
    const books = trilogyBooksMap.get(trilogyId) || []
    let totalChapters = 0
    let chaptersCompleted = 0

    books.forEach((book) => {
      const progress = bookProgressMap.get(book.id)
      if (progress) {
        totalChapters += progress.total_chapters
        chaptersCompleted += progress.chapters_completed
      }
    })

    return { totalChapters, chaptersCompleted, bookCount: books.length }
  }

  const deleteMutation = useMutation({
    mutationFn: deleteTrilogy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trilogies'] })
      toast({
        title: 'Success',
        description: 'Trilogy deleted successfully',
      })
      setTrilogyToDelete(null)
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete trilogy',
        variant: 'destructive',
      })
    },
  })

  const updateTrilogyMutation = useMutation({
    mutationFn: ({ trilogyId, title }: { trilogyId: string; title: string }) =>
      updateTrilogy(trilogyId, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trilogies'] })
      queryClient.invalidateQueries({ queryKey: ['activeTrilogyStats'] })
      toast({
        title: 'Success',
        description: 'Trilogy title updated successfully',
      })
      setEditingTrilogyId(null)
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update trilogy title',
        variant: 'destructive',
      })
    },
  })

  const handleDeleteClick = (e: React.MouseEvent, trilogy: { id: string; title: string }) => {
    e.stopPropagation()
    setTrilogyToDelete(trilogy)
  }

  const handleStartEditTrilogy = (e: React.MouseEvent, trilogyId: string, currentTitle: string) => {
    e.stopPropagation()
    setEditingTrilogyId(trilogyId)
    setEditedTrilogyTitle(currentTitle)
  }

  const handleSaveTrilogyTitle = (e: React.MouseEvent, trilogyId: string) => {
    e.stopPropagation()
    if (editedTrilogyTitle.trim()) {
      updateTrilogyMutation.mutate({ trilogyId, title: editedTrilogyTitle.trim() })
    } else {
      setEditingTrilogyId(null)
    }
  }

  const handleCancelEditTrilogy = (e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingTrilogyId(null)
    setEditedTrilogyTitle('')
  }

  const handleTrilogyTitleKeyDown = (e: React.KeyboardEvent, trilogyId: string) => {
    if (e.key === 'Enter') {
      e.stopPropagation()
      if (editedTrilogyTitle.trim()) {
        updateTrilogyMutation.mutate({ trilogyId, title: editedTrilogyTitle.trim() })
      } else {
        setEditingTrilogyId(null)
      }
    } else if (e.key === 'Escape') {
      setEditingTrilogyId(null)
      setEditedTrilogyTitle('')
    }
  }

  const handleDeleteConfirm = () => {
    if (trilogyToDelete) {
      deleteMutation.mutate(trilogyToDelete.id)
    }
  }

  // Find primary trilogy
  const primaryTrilogy = trilogies?.find(t => t.is_primary)

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      {/* Header Row */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            Welcome back, {profile?.name || user?.email?.split('@')[0]}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {trilogies?.length || 0} {(trilogies?.length || 0) === 1 ? 'trilogy' : 'trilogies'} in your library
          </p>
        </div>
        <Button size="sm" onClick={() => navigate('/trilogy/create')}>
          <Plus className="w-4 h-4 mr-1" />
          New Trilogy
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : trilogies && trilogies.length > 0 ? (
        <div className="space-y-6">
          {/* Primary Trilogy Card */}
          {primaryTrilogy && (() => {
            const stats = getTrilogyChapterStats(primaryTrilogy.id)
            return (
              <Card
                className="border-accent/30 bg-accent/5 cursor-pointer hover:bg-accent/10 transition-colors"
                onClick={() => navigate(`/trilogy/${primaryTrilogy.id}`)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-accent uppercase tracking-wide">Active Project</span>
                      </div>
                      {editingTrilogyId === primaryTrilogy.id ? (
                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          <Input
                            value={editedTrilogyTitle}
                            onChange={(e) => setEditedTrilogyTitle(e.target.value)}
                            onKeyDown={(e) => handleTrilogyTitleKeyDown(e, primaryTrilogy.id)}
                            autoFocus
                            className="h-8 text-lg font-semibold"
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => handleSaveTrilogyTitle(e, primaryTrilogy.id)}
                            disabled={updateTrilogyMutation.isPending}
                            className="h-7 w-7 p-0"
                          >
                            <Check className="w-4 h-4 text-success" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleCancelEditTrilogy}
                            disabled={updateTrilogyMutation.isPending}
                            className="h-7 w-7 p-0"
                          >
                            <X className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 group/title">
                          <h2 className="text-lg font-semibold text-foreground">{primaryTrilogy.title}</h2>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => handleStartEditTrilogy(e, primaryTrilogy.id, primaryTrilogy.title)}
                            className="opacity-0 group-hover/title:opacity-100 transition-opacity h-6 w-6 p-0"
                          >
                            <Pencil className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                      <p className="text-sm text-muted-foreground">by {primaryTrilogy.author}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span>{stats.bookCount} {stats.bookCount === 1 ? 'book' : 'books'}</span>
                        <span className="text-border">•</span>
                        <span>{stats.totalChapters} {stats.totalChapters === 1 ? 'chapter' : 'chapters'}</span>
                        {stats.totalChapters > 0 && (
                          <>
                            <span className="text-border">•</span>
                            <span>{stats.chaptersCompleted} completed</span>
                          </>
                        )}
                      </div>
                    </div>
                    <Button size="sm" variant="outline" className="flex-shrink-0">
                      Continue
                      <ArrowRight className="w-3 h-3 ml-1" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })()}

          {/* All Trilogies Grid */}
          <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-3">
              {primaryTrilogy ? 'All Trilogies' : 'Your Trilogies'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {trilogies.map((trilogy) => {
                const stats = getTrilogyChapterStats(trilogy.id)
                const isPrimary = trilogy.id === primaryTrilogy?.id

                return (
                  <Card
                    key={trilogy.id}
                    onClick={() => navigate(`/trilogy/${trilogy.id}`)}
                    className={`cursor-pointer hover:bg-muted/50 transition-colors ${isPrimary ? 'border-accent/30' : ''}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <BookOpen className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                        <div className="flex gap-1 flex-shrink-0">
                          {isPrimary && (
                            <span className="text-[10px] font-medium text-accent bg-accent/10 px-1.5 py-0.5 rounded">
                              PRIMARY
                            </span>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                            onClick={(e) => handleDeleteClick(e, { id: trilogy.id, title: trilogy.title })}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      {editingTrilogyId === trilogy.id ? (
                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          <Input
                            value={editedTrilogyTitle}
                            onChange={(e) => setEditedTrilogyTitle(e.target.value)}
                            onKeyDown={(e) => handleTrilogyTitleKeyDown(e, trilogy.id)}
                            autoFocus
                            className="h-7 text-sm font-medium"
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => handleSaveTrilogyTitle(e, trilogy.id)}
                            disabled={updateTrilogyMutation.isPending}
                            className="h-6 w-6 p-0"
                          >
                            <Check className="w-3 h-3 text-success" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleCancelEditTrilogy}
                            disabled={updateTrilogyMutation.isPending}
                            className="h-6 w-6 p-0"
                          >
                            <X className="w-3 h-3 text-destructive" />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 group/title">
                          <h3 className="font-medium text-foreground truncate">{trilogy.title}</h3>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => handleStartEditTrilogy(e, trilogy.id, trilogy.title)}
                            className="opacity-0 group-hover/title:opacity-100 transition-opacity h-5 w-5 p-0"
                          >
                            <Pencil className="w-2.5 h-2.5" />
                          </Button>
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground mb-2">by {trilogy.author}</p>

                      {/* Stats Row */}
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{stats.bookCount} {stats.bookCount === 1 ? 'book' : 'books'}</span>
                        <span className="text-border">•</span>
                        <span>{stats.totalChapters} {stats.totalChapters === 1 ? 'ch' : 'chs'}</span>
                        {stats.totalChapters > 0 && stats.chaptersCompleted > 0 && (
                          <>
                            <span className="text-border">•</span>
                            <span className="text-success">{stats.chaptersCompleted} done</span>
                          </>
                        )}
                      </div>

                      {/* Date */}
                      <div className="flex items-center text-[10px] text-muted-foreground mt-2">
                        <Calendar className="w-3 h-3 mr-1" />
                        {new Date(trilogy.created_at).toLocaleDateString()}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 bg-muted/30 rounded border border-border">
          <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-base font-medium text-foreground mb-2">No trilogies yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create your first trilogy to get started
          </p>
          <Button size="sm" onClick={() => navigate('/trilogy/create')}>
            <Plus className="w-4 h-4 mr-1" />
            Create First Trilogy
          </Button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!trilogyToDelete} onOpenChange={(open) => !open && setTrilogyToDelete(null)}>
        <AlertDialogContent className="animate-scale-in">
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete "{trilogyToDelete?.title}" and all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-3">
              The following data will be deleted:
            </p>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              <li>All books in the trilogy</li>
              <li>All chapters and sub-chapters</li>
              <li>All characters</li>
              <li>All world rules</li>
              <li>All generated content</li>
            </ul>
            <p className="mt-4 text-sm font-semibold text-destructive">
              This action cannot be undone.
            </p>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Trilogy'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
