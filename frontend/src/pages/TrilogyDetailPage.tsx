/**
 * Trilogy detail page showing trilogy metadata and books.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query'
import { getTrilogy, getTrilogyBooks, updateBook, updateTrilogy, getUserTrilogies, setPrimaryTrilogy, unsetPrimaryTrilogy } from '@/api/trilogy'
import { getTrilogyCharacters } from '@/api/characters'
import { listWorldRules } from '@/api/worldRules'
import { getBookProgress } from '@/api/chapters'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Calendar, FileText, Globe, Users, Pencil, Check, X, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'

export function TrilogyDetailPage() {
  const { trilogyId } = useParams<{ trilogyId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [editingBookId, setEditingBookId] = useState<string | null>(null)
  const [editedTitle, setEditedTitle] = useState('')
  const [isEditingNarrativeOverview, setIsEditingNarrativeOverview] = useState(false)
  const [editedNarrativeOverview, setEditedNarrativeOverview] = useState('')
  const [isEditingTrilogyTitle, setIsEditingTrilogyTitle] = useState(false)
  const [editedTrilogyTitle, setEditedTrilogyTitle] = useState('')

  const { data: trilogy, isLoading: trilogyLoading } = useQuery({
    queryKey: ['trilogy', trilogyId],
    queryFn: () => getTrilogy(trilogyId!),
    enabled: !!trilogyId,
  })

  const { data: books, isLoading: booksLoading } = useQuery({
    queryKey: ['trilogy', trilogyId, 'books'],
    queryFn: () => getTrilogyBooks(trilogyId!),
    enabled: !!trilogyId,
  })

  // Fetch all trilogies to check for other primary
  const { data: allTrilogies } = useQuery({
    queryKey: ['trilogies'],
    queryFn: getUserTrilogies,
  })

  // Fetch characters count
  const { data: charactersData } = useQuery({
    queryKey: ['characters', trilogyId],
    queryFn: () => getTrilogyCharacters(trilogyId!),
    enabled: !!trilogyId,
  })

  // Fetch world rules count
  const { data: worldRulesData } = useQuery({
    queryKey: ['worldRules', trilogyId],
    queryFn: () => listWorldRules({ trilogy_id: trilogyId! }),
    enabled: !!trilogyId,
  })

  // Fetch book progress for chapter counts
  const bookProgressQueries = useQueries({
    queries: (books || []).map((book) => ({
      queryKey: ['bookProgress', book.id],
      queryFn: () => getBookProgress(book.id),
      enabled: !!book.id,
    })),
  })

  // Create a map of book id to progress data
  const bookProgressMap = new Map(
    bookProgressQueries
      .filter((q) => q.data)
      .map((q) => [q.data!.book_id, q.data!])
  )

  const characterCount = charactersData?.characters?.length || 0
  const worldRulesCount = worldRulesData?.total || 0

  const updateBookMutation = useMutation({
    mutationFn: ({ bookId, title }: { bookId: string; title: string }) =>
      updateBook(bookId, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trilogy', trilogyId, 'books'] })
      toast({
        title: 'Success',
        description: 'Book title updated successfully',
      })
      setEditingBookId(null)
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update book title',
        variant: 'destructive',
      })
    },
  })

  const updateTrilogyMutation = useMutation({
    mutationFn: (data: { title?: string; narrative_overview?: string }) =>
      updateTrilogy(trilogyId!, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['trilogy', trilogyId] })
      queryClient.invalidateQueries({ queryKey: ['trilogies'] })
      queryClient.invalidateQueries({ queryKey: ['activeTrilogyStats'] })
      if (variables.title) {
        toast({
          title: 'Success',
          description: 'Trilogy title updated successfully',
        })
        setIsEditingTrilogyTitle(false)
      }
      if (variables.narrative_overview !== undefined) {
        toast({
          title: 'Success',
          description: 'Narrative overview updated successfully',
        })
        setIsEditingNarrativeOverview(false)
      }
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update trilogy',
        variant: 'destructive',
      })
    },
  })

  const setPrimaryMutation = useMutation({
    mutationFn: setPrimaryTrilogy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trilogy', trilogyId] })
      queryClient.invalidateQueries({ queryKey: ['trilogies'] })
      queryClient.invalidateQueries({ queryKey: ['activeTrilogyStats'] })
      toast({
        title: 'Success',
        description: 'This trilogy is now set as your primary project',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to set primary trilogy',
        variant: 'destructive',
      })
    },
  })

  const unsetPrimaryMutation = useMutation({
    mutationFn: unsetPrimaryTrilogy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trilogy', trilogyId] })
      queryClient.invalidateQueries({ queryKey: ['trilogies'] })
      queryClient.invalidateQueries({ queryKey: ['activeTrilogyStats'] })
      toast({
        title: 'Success',
        description: 'This trilogy is no longer your primary project',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to unset primary trilogy',
        variant: 'destructive',
      })
    },
  })

  // Determine toggle state
  const isPrimaryTrilogy = trilogy?.is_primary || false
  const hasOtherPrimary = allTrilogies?.some(
    (t) => t.is_primary && t.id !== trilogyId
  ) || false

  // Toggle is disabled if another trilogy is primary (must unset that one first)
  // OR if a mutation is pending
  const isToggleDisabled = (hasOtherPrimary && !isPrimaryTrilogy) ||
    setPrimaryMutation.isPending ||
    unsetPrimaryMutation.isPending

  const handlePrimaryToggle = (checked: boolean) => {
    if (!trilogyId) return

    if (checked && !isPrimaryTrilogy) {
      // Turning ON - set this trilogy as primary
      setPrimaryMutation.mutate(trilogyId)
    } else if (!checked && isPrimaryTrilogy) {
      // Turning OFF - unset this trilogy as primary
      unsetPrimaryMutation.mutate(trilogyId)
    }
  }

  const handleStartEdit = (bookId: string, currentTitle: string) => {
    setEditingBookId(bookId)
    setEditedTitle(currentTitle)
  }

  const handleSaveEdit = (bookId: string) => {
    if (editedTitle.trim() && editedTitle.trim() !== '') {
      updateBookMutation.mutate({ bookId, title: editedTitle.trim() })
    } else {
      setEditingBookId(null)
    }
  }

  const handleCancelEdit = () => {
    setEditingBookId(null)
    setEditedTitle('')
  }

  const handleKeyDown = (e: React.KeyboardEvent, bookId: string) => {
    if (e.key === 'Enter') {
      handleSaveEdit(bookId)
    } else if (e.key === 'Escape') {
      handleCancelEdit()
    }
  }

  const handleStartEditNarrativeOverview = () => {
    setEditedNarrativeOverview(trilogy?.narrative_overview || '')
    setIsEditingNarrativeOverview(true)
  }

  const handleSaveNarrativeOverview = () => {
    updateTrilogyMutation.mutate({ narrative_overview: editedNarrativeOverview })
  }

  const handleCancelNarrativeOverview = () => {
    setIsEditingNarrativeOverview(false)
    setEditedNarrativeOverview('')
  }

  const handleStartEditTrilogyTitle = () => {
    setEditedTrilogyTitle(trilogy?.title || '')
    setIsEditingTrilogyTitle(true)
  }

  const handleSaveTrilogyTitle = () => {
    if (editedTrilogyTitle.trim() && editedTrilogyTitle.trim() !== trilogy?.title) {
      updateTrilogyMutation.mutate({ title: editedTrilogyTitle.trim() })
    } else {
      setIsEditingTrilogyTitle(false)
    }
  }

  const handleCancelTrilogyTitle = () => {
    setIsEditingTrilogyTitle(false)
    setEditedTrilogyTitle('')
  }

  const handleTrilogyTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveTrilogyTitle()
    } else if (e.key === 'Escape') {
      handleCancelTrilogyTitle()
    }
  }

  const isLoading = trilogyLoading || booksLoading

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-muted-foreground">Loading trilogy...</p>
      </div>
    )
  }

  if (!trilogy) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Trilogy not found</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      {/* Compact Header Row */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/dashboard')}
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Dashboard
        </Button>
        {/* Primary Toggle */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border text-sm">
          <Label
            htmlFor="primary-toggle"
            className={`text-xs ${
              isToggleDisabled ? 'text-muted-foreground' : 'text-foreground'
            }`}
          >
            Primary
          </Label>
          <Switch
            id="primary-toggle"
            checked={isPrimaryTrilogy}
            disabled={isToggleDisabled}
            onCheckedChange={handlePrimaryToggle}
          />
        </div>
      </div>

      {/* Title & Metadata Section */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {isEditingTrilogyTitle ? (
              <div className="flex items-center gap-2 mb-1">
                <Input
                  value={editedTrilogyTitle}
                  onChange={(e) => setEditedTrilogyTitle(e.target.value)}
                  onKeyDown={handleTrilogyTitleKeyDown}
                  autoFocus
                  className="text-xl font-semibold h-9 max-w-md"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleSaveTrilogyTitle}
                  disabled={updateTrilogyMutation.isPending}
                >
                  <Check className="w-4 h-4 text-success" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleCancelTrilogyTitle}
                  disabled={updateTrilogyMutation.isPending}
                >
                  <X className="w-4 h-4 text-destructive" />
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2 group">
                <h1 className="text-2xl font-semibold text-foreground">{trilogy.title}</h1>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleStartEditTrilogyTitle}
                  className="opacity-0 group-hover:opacity-100 h-7 w-7 p-0"
                >
                  <Pencil className="w-3 h-3" />
                </Button>
              </div>
            )}
            <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
              <span>by {trilogy.author}</span>
              <span className="text-border">•</span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Created {new Date(trilogy.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
              <span className="text-border">•</span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Updated {new Date(trilogy.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
          </div>
        </div>

        {/* Description & Narrative Overview - Compact */}
        {(trilogy.description || trilogy.narrative_overview || isEditingNarrativeOverview) && (
          <div className="mt-4 p-4 bg-muted/30 rounded border border-border">
            {trilogy.description && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {trilogy.description}
              </p>
            )}
            {(trilogy.narrative_overview || isEditingNarrativeOverview) && (
              <div className={trilogy.description ? 'mt-3 pt-3 border-t border-border' : ''}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Narrative Overview</span>
                  {!isEditingNarrativeOverview && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleStartEditNarrativeOverview}
                      className="h-6 px-2 text-xs"
                    >
                      <Pencil className="w-3 h-3 mr-1" />
                      Edit
                    </Button>
                  )}
                </div>
                {isEditingNarrativeOverview ? (
                  <div className="space-y-2">
                    <Textarea
                      value={editedNarrativeOverview}
                      onChange={(e) => setEditedNarrativeOverview(e.target.value)}
                      className="min-h-[100px] text-sm"
                      placeholder="High-level narrative overview..."
                    />
                    <div className="flex gap-2 justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleCancelNarrativeOverview}
                        disabled={updateTrilogyMutation.isPending}
                        className="h-7 text-xs"
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleSaveNarrativeOverview}
                        disabled={updateTrilogyMutation.isPending}
                        className="h-7 text-xs"
                      >
                        {updateTrilogyMutation.isPending ? 'Saving...' : 'Save'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-foreground leading-relaxed">{trilogy.narrative_overview}</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Books Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium">Books</h2>
          <span className="text-sm text-muted-foreground">{books?.length || 0} volumes</span>
        </div>

        {books && books.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {books
              .sort((a, b) => a.book_number - b.book_number)
              .map((book) => {
                const progressPercent = Math.min(
                  (book.current_word_count / book.target_word_count) * 100,
                  100
                )
                const isComplete = progressPercent >= 100
                const isOverTarget = book.current_word_count > book.target_word_count
                const bookProgress = bookProgressMap.get(book.id)
                const chapterCount = bookProgress?.total_chapters || 0
                const chaptersCompleted = bookProgress?.chapters_completed || 0

                return (
                  <Card
                    key={book.id}
                    className="cursor-pointer hover:border-primary/30 transition-colors"
                    onClick={() => navigate(`/book/${book.id}/chapters`)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <div className="w-7 h-7 bg-primary text-primary-foreground rounded flex items-center justify-center font-medium text-sm flex-shrink-0">
                            {book.book_number}
                          </div>
                          {editingBookId === book.id ? (
                            <div className="flex items-center gap-1 flex-1" onClick={(e) => e.stopPropagation()}>
                              <Input
                                value={editedTitle}
                                onChange={(e) => setEditedTitle(e.target.value)}
                                onKeyDown={(e) => handleKeyDown(e, book.id)}
                                onBlur={() => handleSaveEdit(book.id)}
                                autoFocus
                                className="h-7 text-sm"
                              />
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleSaveEdit(book.id)}
                                disabled={updateBookMutation.isPending}
                                className="h-7 w-7 p-0"
                              >
                                <Check className="w-3 h-3 text-success" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={handleCancelEdit}
                                disabled={updateBookMutation.isPending}
                                className="h-7 w-7 p-0"
                              >
                                <X className="w-3 h-3 text-destructive" />
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1 flex-1 min-w-0 group">
                              <span className="font-medium text-sm truncate">{book.title}</span>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleStartEdit(book.id, book.title)
                                }}
                                className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0 flex-shrink-0"
                              >
                                <Pencil className="w-3 h-3" />
                              </Button>
                            </div>
                          )}
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded flex-shrink-0 ${
                          isComplete
                            ? 'bg-success/10 text-success'
                            : isOverTarget
                            ? 'bg-warning/10 text-warning'
                            : book.current_word_count > 0
                            ? 'bg-accent/10 text-accent'
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          {isComplete ? 'Complete' : isOverTarget ? 'Over Target' : book.current_word_count > 0 ? 'In Progress' : 'Not Started'}
                        </span>
                      </div>

                      {/* Chapter Stats */}
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
                        <span>{chapterCount} {chapterCount === 1 ? 'chapter' : 'chapters'}</span>
                        {chapterCount > 0 && (
                          <>
                            <span className="text-border">•</span>
                            <span>{chaptersCompleted} completed</span>
                          </>
                        )}
                      </div>

                      {/* Progress */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">
                            {book.current_word_count.toLocaleString()} / {book.target_word_count.toLocaleString()} words
                          </span>
                          <span className="font-medium">{progressPercent.toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
                          <div
                            className="h-1.5 rounded-full bg-primary transition-all"
                            style={{ width: `${progressPercent}%` }}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center">
              <FileText className="w-10 h-10 text-muted-foreground mx-auto mb-2 opacity-50" />
              <p className="text-sm font-medium mb-1">No books found</p>
              <p className="text-xs text-muted-foreground">Books will appear here once created</p>
            </CardContent>
          </Card>
        )}

        {/* Trilogy Tools */}
        <div className="mt-6 pt-6 border-t border-border">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/trilogy/${trilogyId}/characters`)}
            >
              <Users className="w-4 h-4 mr-1" />
              Characters
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-muted rounded">{characterCount}</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/trilogy/${trilogyId}/world-rules`)}
            >
              <Globe className="w-4 h-4 mr-1" />
              World Rules
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-muted rounded">{worldRulesCount}</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/trilogy/${trilogyId}/rule-analytics`)}
            >
              <BarChart3 className="w-4 h-4 mr-1" />
              Analytics
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}