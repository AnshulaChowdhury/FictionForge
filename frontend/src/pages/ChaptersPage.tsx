/**
 * Chapters page for managing book chapters (Epic 4).
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import {
  DndContext,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  MeasuringStrategy,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  getBookChapters,
  createChapter,
  updateChapter,
  deleteChapter,
  reorderChapter,
  getBookProgress,
} from '@/api/chapters'
import type { Chapter, CreateChapterRequest, UpdateChapterRequest } from '@/api/chapters'
import { getBook } from '@/api/trilogy'
import { getTrilogyCharacters } from '@/api/characters'
import { ArrowLeft, Plus, Edit, Trash2, BookOpen, GripVertical, User, FileText, MoreVertical, Search, LayoutGrid, List } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

type ViewMode = 'list' | 'card'

interface SortableChapterCardProps {
  chapter: Chapter
  progress: {
    percentage: number
    status: 'not_started' | 'in_progress' | 'complete' | 'over_target'
  }
  getCharacterName: (characterId: string) => string
  getStatusColor: (status: string) => string
  onEdit: (chapter: Chapter) => void
  onDelete: (chapter: Chapter) => void
  onViewSubChapters: (chapter: Chapter) => void
}

function SortableChapterCard({
  chapter,
  progress,
  getCharacterName,
  getStatusColor,
  onEdit,
  onDelete,
  onViewSubChapters,
}: SortableChapterCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: chapter.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onEdit(chapter)}
      onDoubleClick={() => onEdit(chapter)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <Badge variant="outline" className="font-mono">
                Ch. {chapter.chapter_number}
              </Badge>
              <CardTitle className="text-xl">{chapter.title}</CardTitle>
              <Badge
                variant="secondary"
                className={getStatusColor(progress.status)}
              >
                {progress.status.replace('_', ' ')}
              </Badge>
            </div>
            {chapter.chapter_plot && (
              <CardDescription className="mt-2">
                {chapter.chapter_plot}
              </CardDescription>
            )}
            <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              <span>POV: {getCharacterName(chapter.character_id)}</span>
            </div>
          </div>
          <div className="flex gap-2 items-center">
            <Button
              variant="ghost"
              size="icon"
              {...attributes}
              {...listeners}
              title="Drag to reorder"
              className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
            >
              <GripVertical className="h-4 w-4" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                  <MoreVertical className="h-4 w-4" />
                  <span className="sr-only">Open menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={() => onViewSubChapters(chapter)}>
                  <FileText className="mr-2 h-4 w-4" />
                  View Sub-chapters
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit(chapter)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit Chapter
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => onDelete(chapter)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Chapter
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      {chapter.target_word_count && (
        <CardContent>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Progress</span>
              <span className="text-sm text-muted-foreground">
                {chapter.current_word_count.toLocaleString()} / {chapter.target_word_count.toLocaleString()} words
              </span>
            </div>
            <Progress value={progress.percentage} className="h-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {progress.percentage.toFixed(1)}% complete
            </p>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

interface SortableChapterListItemProps {
  chapter: Chapter
  progress: {
    percentage: number
    status: 'not_started' | 'in_progress' | 'complete' | 'over_target'
  }
  getCharacterName: (characterId: string) => string
  getStatusColor: (status: string) => string
  truncateText: (text: string | undefined, maxLength?: number) => string
  onEdit: (chapter: Chapter) => void
  onDelete: (chapter: Chapter) => void
  onViewSubChapters: (chapter: Chapter) => void
}

function SortableChapterListItem({
  chapter,
  progress,
  getCharacterName,
  getStatusColor,
  truncateText,
  onEdit,
  onDelete,
  onViewSubChapters,
}: SortableChapterListItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: chapter.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-start gap-4 p-4 hover:bg-muted/50 transition-colors cursor-pointer"
      onClick={() => onEdit(chapter)}
      onDoubleClick={() => onEdit(chapter)}
    >
      <Button
        variant="ghost"
        size="icon"
        {...attributes}
        {...listeners}
        title="Drag to reorder"
        className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground flex-shrink-0 mt-1"
      >
        <GripVertical className="h-4 w-4" />
      </Button>
      <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center flex-shrink-0">
        <BookOpen className="w-5 h-5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className="font-mono text-xs">
                Ch. {chapter.chapter_number}
              </Badge>
              <h3 className="font-medium text-foreground">{chapter.title}</h3>
              <Badge
                variant="secondary"
                className={cn('text-xs', getStatusColor(progress.status))}
              >
                {progress.status.replace('_', ' ')}
              </Badge>
            </div>
            {chapter.chapter_plot && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {truncateText(chapter.chapter_plot, 150)}
              </p>
            )}
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                POV: {getCharacterName(chapter.character_id)}
              </span>
              {chapter.target_word_count && (
                <span>
                  {chapter.current_word_count.toLocaleString()} / {chapter.target_word_count.toLocaleString()} words ({progress.percentage.toFixed(0)}%)
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-1 flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewSubChapters(chapter)}
              title="View sub-chapters"
            >
              <FileText className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(chapter)}
              title="Edit"
            >
              <Edit className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(chapter)}
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ChaptersPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingChapter, setEditingChapter] = useState<Chapter | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [deletingChapter, setDeletingChapter] = useState<Chapter | null>(null)
  const [isReorderDialogOpen, setIsReorderDialogOpen] = useState(false)
  const [reorderingChapter, setReorderingChapter] = useState<Chapter | null>(null)
  const [newPosition, setNewPosition] = useState<number>(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('card')

  const [formData, setFormData] = useState({
    title: '',
    chapter_plot: '',
    character_id: '',
    target_word_count: '',
  })

  // Fetch book details
  const { data: book } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => getBook(bookId!),
    enabled: !!bookId,
  })

  // Fetch chapters for the book
  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters', bookId],
    queryFn: () => getBookChapters(bookId!),
    enabled: !!bookId,
  })

  // Fetch book progress
  const { data: progressData } = useQuery({
    queryKey: ['bookProgress', bookId],
    queryFn: () => getBookProgress(bookId!),
    enabled: !!bookId,
  })

  // Fetch characters for POV dropdown (need trilogy_id from book)
  const { data: charactersData, isLoading: charactersLoading, error: charactersError } = useQuery({
    queryKey: ['characters', book?.trilogy_id],
    queryFn: () => getTrilogyCharacters(book!.trilogy_id),
    enabled: !!book?.trilogy_id,
  })

  const createMutation = useMutation({
    mutationFn: createChapter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', bookId] })
      queryClient.invalidateQueries({ queryKey: ['bookProgress', bookId] })
      setIsCreateDialogOpen(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateChapterRequest }) =>
      updateChapter(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', bookId] })
      queryClient.invalidateQueries({ queryKey: ['bookProgress', bookId] })
      setIsEditDialogOpen(false)
      setEditingChapter(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteChapter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', bookId] })
      queryClient.invalidateQueries({ queryKey: ['bookProgress', bookId] })
      setIsDeleteDialogOpen(false)
      setDeletingChapter(null)
    },
  })

  const reorderMutation = useMutation({
    mutationFn: ({ chapterId, newPosition }: { chapterId: string; newPosition: number }) =>
      reorderChapter(chapterId, newPosition),
    // Optimistic update - update UI immediately before server responds
    onMutate: async ({ chapterId, newPosition }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['chapters', bookId] })

      // Snapshot the previous value
      const previousChapters = queryClient.getQueryData(['chapters', bookId])

      // Optimistically update the cache
      queryClient.setQueryData(['chapters', bookId], (old: any) => {
        if (!old?.chapters) return old
        const chapters = [...old.chapters]
        const oldIndex = chapters.findIndex((ch: Chapter) => ch.id === chapterId)
        const newIndex = newPosition - 1

        if (oldIndex !== -1 && newIndex >= 0 && newIndex < chapters.length) {
          const reordered = arrayMove(chapters, oldIndex, newIndex)
          // Update chapter numbers
          reordered.forEach((ch: Chapter, idx: number) => {
            ch.chapter_number = idx + 1
          })
          return { ...old, chapters: reordered }
        }
        return old
      })

      return { previousChapters }
    },
    // If mutation fails, roll back to previous value
    onError: (_err, _variables, context) => {
      if (context?.previousChapters) {
        queryClient.setQueryData(['chapters', bookId], context.previousChapters)
      }
    },
    // Always refetch after error or success to ensure sync with server
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', bookId] })
      setIsReorderDialogOpen(false)
      setReorderingChapter(null)
      setNewPosition(1)
    },
  })

  const resetForm = () => {
    setFormData({
      title: '',
      chapter_plot: '',
      character_id: '',
      target_word_count: '',
    })
  }

  const handleCreate = () => {
    const request: CreateChapterRequest = {
      book_id: bookId!,
      character_id: formData.character_id,
      title: formData.title,
      chapter_plot: formData.chapter_plot || undefined,
      target_word_count: formData.target_word_count ? parseInt(formData.target_word_count) : undefined,
    }

    createMutation.mutate(request)
  }

  const handleEdit = () => {
    if (!editingChapter) return

    const data: UpdateChapterRequest = {
      title: formData.title,
      chapter_plot: formData.chapter_plot || undefined,
      character_id: formData.character_id || undefined,
      target_word_count: formData.target_word_count ? parseInt(formData.target_word_count) : undefined,
    }

    updateMutation.mutate({
      id: editingChapter.id,
      data,
    })
  }

  const openEditDialog = (chapter: Chapter) => {
    setEditingChapter(chapter)
    setFormData({
      title: chapter.title,
      chapter_plot: chapter.chapter_plot || '',
      character_id: chapter.character_id,
      target_word_count: chapter.target_word_count?.toString() || '',
    })
    setIsEditDialogOpen(true)
  }

  const openDeleteDialog = (chapter: Chapter) => {
    setDeletingChapter(chapter)
    setIsDeleteDialogOpen(true)
  }

  const handleReorder = () => {
    if (!reorderingChapter) return
    reorderMutation.mutate({
      chapterId: reorderingChapter.id,
      newPosition,
    })
  }

  const getCharacterName = (characterId: string) => {
    const character = charactersData?.characters.find(c => c.id === characterId)
    return character?.name || 'Unknown Character'
  }

  const calculateProgress = (chapter: Chapter) => {
    if (!chapter.target_word_count || chapter.target_word_count === 0) {
      return { percentage: 0, status: 'not_started' as const }
    }
    const percentage = (chapter.current_word_count / chapter.target_word_count) * 100
    let status: 'not_started' | 'in_progress' | 'complete' | 'over_target'
    if (chapter.current_word_count === 0) {
      status = 'not_started'
    } else if (percentage >= 110) {
      status = 'over_target'
    } else if (percentage >= 100) {
      status = 'complete'
    } else {
      status = 'in_progress'
    }
    return { percentage: Math.min(percentage, 100), status }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete':
        return 'bg-success text-success-foreground'
      case 'in_progress':
        return 'bg-accent text-accent-foreground'
      case 'over_target':
        return 'bg-warning text-warning-foreground'
      default:
        return 'bg-muted text-muted-foreground'
    }
  }

  // Helper to truncate text for excerpts
  const truncateText = (text: string | undefined, maxLength: number = 120) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength).trim() + '...'
  }

  // Filter chapters based on search query
  const chapters = chaptersData?.chapters || []
  const filteredChapters = useMemo(() => {
    if (!searchQuery.trim()) return chapters
    const query = searchQuery.toLowerCase()
    return chapters.filter(
      (chapter) =>
        chapter.title.toLowerCase().includes(query) ||
        chapter.chapter_plot?.toLowerCase().includes(query) ||
        getCharacterName(chapter.character_id).toLowerCase().includes(query)
    )
  }, [chapters, searchQuery])

  // Drag-and-drop sensors with activation constraints for smoother UX
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Require 8px movement before drag starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Measuring configuration for better drop detection
  const measuringConfig = {
    droppable: {
      strategy: MeasuringStrategy.Always,
    },
  }

  // Track the last valid over target during drag
  const [lastOverId, setLastOverId] = useState<string | null>(null)

  // Handle drag over - track the current over target
  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event
    if (over) {
      setLastOverId(over.id as string)
    }
  }

  // Handle drag end - use lastOverId if over is null
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    // Use the last known over target if current over is null
    const targetId = over?.id ?? lastOverId

    // Reset tracking state
    setLastOverId(null)

    if (!targetId || active.id === targetId) {
      return
    }

    const oldIndex = chapters.findIndex((ch) => ch.id === active.id)
    const newIndex = chapters.findIndex((ch) => ch.id === targetId)

    if (oldIndex !== -1 && newIndex !== -1) {
      // Calculate the new chapter number (1-indexed)
      const newPosition = newIndex + 1

      // Call reorder API
      reorderMutation.mutate({
        chapterId: active.id as string,
        newPosition,
      })
    }
  }

  // Calculate progress percentage
  const progressPercentage = progressData?.overall_percentage || 0
  const chaptersCompleted = progressData?.chapters_completed || 0
  const totalChapters = progressData?.total_chapters || 0

  if (chaptersLoading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-8">
        <p className="text-muted-foreground">Loading chapters...</p>
      </div>
    )
  }

  return (
    <>
      {/* Sticky Header - Always present, compact design */}
      <div className="sticky top-0 z-40 bg-background/95 backdrop-blur-sm border-b border-border/50">
        <div className="max-w-6xl mx-auto px-6 py-2.5 flex items-center justify-between gap-4">
          {/* Back + Title */}
          <div className="flex items-center gap-3 min-w-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="h-7 px-2 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <h1 className="text-sm font-semibold text-foreground truncate">
              {book?.title || 'Book'} - Chapters
            </h1>
          </div>

          {/* Progress Indicator */}
          {progressData && (
            <div className="hidden sm:flex items-center gap-3 flex-1 max-w-xs">
              <div className="flex items-center gap-2 text-xs text-muted-foreground whitespace-nowrap">
                <span>{chaptersCompleted}/{totalChapters}</span>
                <span className="text-border">•</span>
                <span>{progressPercentage.toFixed(0)}%</span>
              </div>
              <div className="flex-1 bg-secondary rounded-full h-1 overflow-hidden min-w-[40px]">
                <div
                  className="h-1 rounded-full bg-primary transition-all"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>
          )}

          {/* Add Chapter Button */}
          <Button
            size="sm"
            onClick={() => setIsCreateDialogOpen(true)}
            className="flex-shrink-0 h-7 text-xs"
          >
            <Plus className="mr-1 h-3 w-3" />
            Add
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {/* Full Progress Card */}
        {progressData && (
          <div className="mb-6 p-4 bg-muted/30 rounded border border-border">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">
                  {progressData.total_chapters} chapters
                </span>
                <span className="text-border">•</span>
                <span className="text-muted-foreground">
                  {progressData.chapters_completed} completed
                </span>
                <span className="text-border">•</span>
                <span className="text-muted-foreground">
                  {progressData.total_current_word_count.toLocaleString()} / {progressData.total_target_word_count.toLocaleString()} words
                </span>
              </div>
              <span className="text-sm font-medium">{progressData.overall_percentage.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
              <div
                className="h-1.5 rounded-full bg-primary transition-all"
                style={{ width: `${progressData.overall_percentage}%` }}
              />
            </div>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-muted" />
                {progressData.chapters_by_status.not_started} Not Started
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-accent" />
                {progressData.chapters_by_status.in_progress} In Progress
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-success" />
                {progressData.chapters_by_status.complete} Complete
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-warning" />
                {progressData.chapters_by_status.over_target} Over Target
              </span>
            </div>
          </div>
        )}

        {/* Search and View Toggle */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search chapters by title, plot, or POV character..."
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* View Toggle */}
        <div className="flex border rounded overflow-hidden">
          <button
            type="button"
            onClick={() => setViewMode('list')}
            className={cn(
              'p-2 transition-colors',
              viewMode === 'list' ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
            )}
            title="List view"
          >
            <List className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setViewMode('card')}
            className={cn(
              'p-2 transition-colors',
              viewMode === 'card' ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
            )}
            title="Card view"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chapters List */}
      {chapters.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <BookOpen className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No chapters yet</h3>
            <p className="text-muted-foreground mb-4">
              Start planning your book by creating the first chapter
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create First Chapter
            </Button>
          </CardContent>
        </Card>
      ) : filteredChapters.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No chapters found</h3>
            <p className="text-muted-foreground mb-4">
              Try adjusting your search query
            </p>
          </CardContent>
        </Card>
      ) : viewMode === 'list' ? (
        /* List View */
        <DndContext
          key="list-view"
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          measuring={measuringConfig}
        >
          <SortableContext
            items={filteredChapters.map((ch) => ch.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="border rounded divide-y">
              {filteredChapters.map((chapter) => {
                const progress = calculateProgress(chapter)
                return (
                  <SortableChapterListItem
                    key={chapter.id}
                    chapter={chapter}
                    progress={progress}
                    getCharacterName={getCharacterName}
                    getStatusColor={getStatusColor}
                    truncateText={truncateText}
                    onEdit={openEditDialog}
                    onDelete={openDeleteDialog}
                    onViewSubChapters={(chapter) => navigate(`/chapter/${chapter.id}/sub-chapters`)}
                  />
                )
              })}
            </div>
          </SortableContext>
        </DndContext>
      ) : (
        /* Card View */
        <DndContext
          key="card-view"
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          measuring={measuringConfig}
        >
          <SortableContext
            items={filteredChapters.map((ch) => ch.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="grid gap-4">
              {filteredChapters.map((chapter) => {
                const progress = calculateProgress(chapter)
                return (
                  <SortableChapterCard
                    key={chapter.id}
                    chapter={chapter}
                    progress={progress}
                    getCharacterName={getCharacterName}
                    getStatusColor={getStatusColor}
                    onEdit={openEditDialog}
                    onDelete={openDeleteDialog}
                    onViewSubChapters={(chapter) => navigate(`/chapter/${chapter.id}/sub-chapters`)}
                  />
                )
              })}
            </div>
          </SortableContext>
        </DndContext>
      )}
      </div> {/* End Content Section */}

      {/* Create Chapter Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Chapter</DialogTitle>
            <DialogDescription>
              Add a new chapter to {book?.title}. Chapter number will be assigned automatically.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">Chapter Title *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="The Awakening"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="character">POV Character *</Label>
              <Select
                value={formData.character_id}
                onValueChange={(value) => setFormData({ ...formData, character_id: value })}
                disabled={charactersLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder={
                    charactersLoading
                      ? "Loading characters..."
                      : charactersData?.characters.length === 0
                      ? "No characters available"
                      : "Select character"
                  } />
                </SelectTrigger>
                <SelectContent>
                  {charactersLoading ? (
                    <div className="p-2 text-sm text-muted-foreground">Loading...</div>
                  ) : charactersError ? (
                    <div className="p-2 text-sm text-red-500">Error loading characters</div>
                  ) : charactersData?.characters.length === 0 ? (
                    <div className="p-2 text-sm text-muted-foreground">No characters found. Create characters first.</div>
                  ) : (
                    charactersData?.characters.map((character) => (
                      <SelectItem key={character.id} value={character.id}>
                        {character.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              {charactersError && (
                <p className="text-sm text-red-500">Failed to load characters. Please try again.</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Plot Notes</Label>
              <Textarea
                id="description"
                value={formData.chapter_plot}
                onChange={(e) => setFormData({ ...formData, chapter_plot: e.target.value })}
                placeholder="Brief description of what happens in this chapter..."
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="target_word_count">Target Word Count</Label>
              <Input
                id="target_word_count"
                type="number"
                value={formData.target_word_count}
                onChange={(e) => setFormData({ ...formData, target_word_count: e.target.value })}
                placeholder="3000"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateDialogOpen(false)
                resetForm()
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!formData.title || !formData.character_id || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Chapter'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Chapter Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Chapter</DialogTitle>
            <DialogDescription>
              Update chapter details for "{editingChapter?.title}"
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-title">Chapter Title *</Label>
              <Input
                id="edit-title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-character">POV Character</Label>
              <Select
                value={formData.character_id}
                onValueChange={(value) => setFormData({ ...formData, character_id: value })}
                disabled={charactersLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder={
                    charactersLoading
                      ? "Loading characters..."
                      : "Select character"
                  } />
                </SelectTrigger>
                <SelectContent>
                  {charactersLoading ? (
                    <div className="p-2 text-sm text-muted-foreground">Loading...</div>
                  ) : charactersError ? (
                    <div className="p-2 text-sm text-red-500">Error loading characters</div>
                  ) : charactersData?.characters.length === 0 ? (
                    <div className="p-2 text-sm text-muted-foreground">No characters found. Create characters first.</div>
                  ) : (
                    charactersData?.characters.map((character) => (
                      <SelectItem key={character.id} value={character.id}>
                        {character.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Plot Notes</Label>
              <Textarea
                id="edit-description"
                value={formData.chapter_plot}
                onChange={(e) => setFormData({ ...formData, chapter_plot: e.target.value })}
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-target_word_count">Target Word Count</Label>
              <Input
                id="edit-target_word_count"
                type="number"
                value={formData.target_word_count}
                onChange={(e) => setFormData({ ...formData, target_word_count: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                if (editingChapter) {
                  navigate(`/chapter/${editingChapter.id}/sub-chapters`)
                }
              }}
              className="sm:mr-auto"
            >
              <FileText className="mr-2 h-4 w-4" />
              View Sub-Chapters
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setIsEditDialogOpen(false)
                  setEditingChapter(null)
                  resetForm()
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleEdit}
                disabled={!formData.title || updateMutation.isPending}
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Chapter</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingChapter?.title}"?
              This action cannot be undone. Subsequent chapters will be automatically renumbered.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsDeleteDialogOpen(false)
                setDeletingChapter(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deletingChapter) {
                  deleteMutation.mutate(deletingChapter.id)
                }
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reorder Chapter Dialog */}
      <Dialog open={isReorderDialogOpen} onOpenChange={setIsReorderDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reorder Chapter</DialogTitle>
            <DialogDescription>
              Move "{reorderingChapter?.title}" to a new position. Other chapters will be automatically renumbered.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="new-position">New Position</Label>
              <Input
                id="new-position"
                type="number"
                min="1"
                max={chapters.length}
                value={newPosition}
                onChange={(e) => setNewPosition(parseInt(e.target.value) || 1)}
              />
              <p className="text-sm text-muted-foreground">
                Current position: {reorderingChapter?.chapter_number} of {chapters.length}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsReorderDialogOpen(false)
                setReorderingChapter(null)
                setNewPosition(1)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleReorder}
              disabled={reorderMutation.isPending || newPosition === reorderingChapter?.chapter_number}
            >
              {reorderMutation.isPending ? 'Reordering...' : 'Reorder'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
