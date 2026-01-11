/**
 * Sub-Chapters page for managing chapter sub-chapters (Epic 6).
 */

import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
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
  getChapterSubChapters,
  createSubChapter,
  updateSubChapter,
  deleteSubChapter,
  reorderSubChapter,
  getChapterProgress,
  regenerateSubChapter,
  getContentReviewFlags,
  resolveContentReviewFlag,
  updateSubChapterContent,
} from '@/api/subChapters'
import { cancelJob } from '@/api/generationJobs'
import type {
  SubChapter,
  CreateSubChapterRequest,
  UpdateSubChapterRequest,
  UpdateSubChapterContentRequest,
  SubChapterRegenerateRequest,
} from '@/api/subChapters'
import { getChapter } from '@/api/chapters'
import { getBook } from '@/api/trilogy'
import { ArrowLeft, Plus, Edit, Trash2, FileText, GripVertical, RotateCw, History, AlertCircle, Sparkles, Pencil, Save, X, Maximize2, MoreVertical, Search, LayoutGrid, List } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { RulePreviewDialog } from '@/components/world-rules/RulePreviewDialog'
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
import { VersionHistoryDialog } from '@/components/VersionHistoryDialog'
import { InlineJobProgress } from '@/components/job-progress'
import { ZenMode } from '@/components/ZenMode'

type ViewMode = 'list' | 'card'

interface SortableSubChapterCardProps {
  subChapter: SubChapter
  progress: {
    percentage: number
    status: 'not_started' | 'in_progress' | 'near_complete' | 'complete'
  }
  getStatusColor: (status: string) => string
  onEdit: (subChapter: SubChapter) => void
  onDelete: (subChapter: SubChapter) => void
  onRegenerate: (subChapter: SubChapter) => void
  onViewVersions: (subChapter: SubChapter) => void
  onViewFlags: (subChapter: SubChapter) => void
  onViewContent: (subChapter: SubChapter) => void
  flagCount: number
  chapterId?: string
  queryClient?: any
}

function SortableSubChapterCard({
  subChapter,
  progress,
  getStatusColor,
  onEdit,
  onDelete,
  onRegenerate,
  onViewVersions,
  onViewFlags,
  onViewContent,
  flagCount,
  chapterId,
  queryClient,
}: SortableSubChapterCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: subChapter.id })

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
      onClick={() => onEdit(subChapter)}
      onDoubleClick={() => onEdit(subChapter)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <Badge variant="outline" className="font-mono">
                {subChapter.sub_chapter_number}
              </Badge>
              {subChapter.title && (
                <CardTitle className="text-lg">{subChapter.title}</CardTitle>
              )}
              <Badge
                variant="secondary"
                className={getStatusColor(subChapter.status)}
              >
                {subChapter.status.replace('_', ' ')}
              </Badge>
              {flagCount > 0 && (
                <Badge variant="destructive" className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {flagCount} flag{flagCount > 1 ? 's' : ''}
                </Badge>
              )}
            </div>
            {subChapter.plot_points && (
              <CardDescription className="mt-2">
                {subChapter.plot_points}
              </CardDescription>
            )}
            {subChapter.content && (
              <div className="mt-3 text-sm text-muted-foreground">
                <p className="line-clamp-2">{subChapter.content}</p>
              </div>
            )}
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
                <DropdownMenuItem
                  onClick={() => onViewContent(subChapter)}
                  disabled={!subChapter.content}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  View Content
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewVersions(subChapter)}>
                  <History className="mr-2 h-4 w-4" />
                  Version History
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onRegenerate(subChapter)}>
                  <RotateCw className="mr-2 h-4 w-4" />
                  Regenerate
                </DropdownMenuItem>
                {flagCount > 0 && (
                  <DropdownMenuItem onClick={() => onViewFlags(subChapter)}>
                    <AlertCircle className="mr-2 h-4 w-4 text-destructive" />
                    Review Flags ({flagCount})
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onEdit(subChapter)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit Details
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onDelete(subChapter)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      {/* Epic 10: Show inline progress when generating */}
      {subChapter.status === 'in_progress' && subChapter.generation_job_id && chapterId && queryClient && (
        <CardContent>
          <InlineJobProgress
            jobId={subChapter.generation_job_id}
            onComplete={() => {
              // Refetch sub-chapters to update status
              queryClient.invalidateQueries(['sub-chapters', chapterId])
            }}
            onCancel={async () => {
              try {
                await cancelJob(subChapter.generation_job_id!)
                queryClient.invalidateQueries(['sub-chapters', chapterId])
              } catch (error) {
                console.error('Failed to cancel job:', error)
              }
            }}
          />
        </CardContent>
      )}

      {/* Show word count progress for completed sub-chapters */}
      {subChapter.word_count > 0 && subChapter.status !== 'in_progress' && (
        <CardContent>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Progress</span>
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

interface SortableSubChapterListItemProps {
  subChapter: SubChapter
  progress: {
    percentage: number
    status: 'not_started' | 'in_progress' | 'near_complete' | 'complete'
  }
  getStatusColor: (status: string) => string
  truncateText: (text: string | undefined, maxLength?: number) => string
  onEdit: (subChapter: SubChapter) => void
  onDelete: (subChapter: SubChapter) => void
  onRegenerate: (subChapter: SubChapter) => void
  onViewVersions: (subChapter: SubChapter) => void
  onViewFlags: (subChapter: SubChapter) => void
  onViewContent: (subChapter: SubChapter) => void
  flagCount: number
  chapterId?: string
  queryClient?: any
}

function SortableSubChapterListItem({
  subChapter,
  progress,
  getStatusColor,
  truncateText,
  onEdit,
  onDelete,
  onRegenerate,
  onViewVersions,
  onViewFlags,
  onViewContent,
  flagCount,
  chapterId,
  queryClient,
}: SortableSubChapterListItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: subChapter.id })

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
      onClick={() => onEdit(subChapter)}
      onDoubleClick={() => onEdit(subChapter)}
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
        <FileText className="w-5 h-5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className="font-mono text-xs">
                {subChapter.sub_chapter_number}
              </Badge>
              {subChapter.title && (
                <h3 className="font-medium text-foreground">{subChapter.title}</h3>
              )}
              <Badge
                variant="secondary"
                className={cn('text-xs', getStatusColor(subChapter.status))}
              >
                {subChapter.status.replace('_', ' ')}
              </Badge>
              {flagCount > 0 && (
                <Badge variant="destructive" className="flex items-center gap-1 text-xs">
                  <AlertCircle className="h-3 w-3" />
                  {flagCount}
                </Badge>
              )}
            </div>
            {subChapter.plot_points && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {truncateText(subChapter.plot_points, 150)}
              </p>
            )}
            {subChapter.content && (
              <p className="text-xs text-muted-foreground/70 mt-1 italic line-clamp-1">
                {truncateText(subChapter.content, 100)}
              </p>
            )}
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              <span>{subChapter.word_count.toLocaleString()} words</span>
              {progress.percentage > 0 && (
                <span>({progress.percentage.toFixed(0)}% complete)</span>
              )}
            </div>
          </div>
          <div className="flex gap-1 flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewContent(subChapter)}
              disabled={!subChapter.content}
              title="View content"
            >
              <FileText className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewVersions(subChapter)}
              title="Version history"
            >
              <History className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRegenerate(subChapter)}
              title="Regenerate"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
            {flagCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onViewFlags(subChapter)}
                title={`Review ${flagCount} flag${flagCount > 1 ? 's' : ''}`}
              >
                <AlertCircle className="w-4 h-4 text-destructive" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(subChapter)}
              title="Edit"
            >
              <Edit className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(subChapter)}
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
        {/* Epic 10: Show inline progress when generating */}
        {subChapter.status === 'in_progress' && subChapter.generation_job_id && chapterId && queryClient && (
          <div className="mt-3">
            <InlineJobProgress
              jobId={subChapter.generation_job_id}
              onComplete={() => {
                queryClient.invalidateQueries(['sub-chapters', chapterId])
              }}
              onCancel={async () => {
                try {
                  await cancelJob(subChapter.generation_job_id!)
                  queryClient.invalidateQueries(['sub-chapters', chapterId])
                } catch (error) {
                  console.error('Failed to cancel job:', error)
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export function SubChaptersPage() {
  const { chapterId } = useParams<{ chapterId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [isRegenerateDialogOpen, setIsRegenerateDialogOpen] = useState(false)
  const [isVersionsDialogOpen, setIsVersionsDialogOpen] = useState(false)
  const [isFlagsDialogOpen, setIsFlagsDialogOpen] = useState(false)
  const [isContentDialogOpen, setIsContentDialogOpen] = useState(false)
  const [isRulePreviewDialogOpen, setIsRulePreviewDialogOpen] = useState(false)

  const [editingSubChapter, setEditingSubChapter] = useState<SubChapter | null>(null)
  const [deletingSubChapter, setDeletingSubChapter] = useState<SubChapter | null>(null)
  const [regeneratingSubChapter, setRegeneratingSubChapter] = useState<SubChapter | null>(null)
  const [viewingVersionsSubChapter, setViewingVersionsSubChapter] = useState<SubChapter | null>(null)
  const [viewingFlagsSubChapter, setViewingFlagsSubChapter] = useState<SubChapter | null>(null)
  const [viewingContentSubChapter, setViewingContentSubChapter] = useState<SubChapter | null>(null)

  const [isEditingContent, setIsEditingContent] = useState(false)
  const [editedContent, setEditedContent] = useState('')
  const [editContentDescription, setEditContentDescription] = useState('')
  const [isZenModeOpen, setIsZenModeOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('card')

  const [formData, setFormData] = useState<{
    title: string
    plot_points: string
    status: 'draft' | 'in_progress' | 'completed' | 'needs_review'
  }>({
    title: '',
    plot_points: '',
    status: 'draft',
  })

  // Fetch chapter details
  const { data: chapter } = useQuery({
    queryKey: ['chapter', chapterId],
    queryFn: () => getChapter(chapterId!),
    enabled: !!chapterId,
  })

  // Fetch book details (for trilogy_id in Epic 5B)
  const { data: book } = useQuery({
    queryKey: ['book', chapter?.book_id],
    queryFn: () => getBook(chapter!.book_id),
    enabled: !!chapter?.book_id,
  })

  // Fetch sub-chapters
  const { data: subChapters = [], isLoading: subChaptersLoading } = useQuery({
    queryKey: ['subChapters', chapterId],
    queryFn: () => getChapterSubChapters(chapterId!),
    enabled: !!chapterId,
  })

  // Fetch progress
  const { data: progressData } = useQuery({
    queryKey: ['chapterProgress', chapterId],
    queryFn: () => getChapterProgress(chapterId!),
    enabled: !!chapterId,
  })

  // Fetch flags for selected sub-chapter
  const { data: flags = [] } = useQuery({
    queryKey: ['subChapterFlags', viewingFlagsSubChapter?.id],
    queryFn: () => getContentReviewFlags(viewingFlagsSubChapter!.id),
    enabled: !!viewingFlagsSubChapter,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createSubChapter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
      queryClient.invalidateQueries({ queryKey: ['chapterProgress', chapterId] })
      setIsCreateDialogOpen(false)
      resetForm()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSubChapterRequest }) =>
      updateSubChapter(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
      queryClient.invalidateQueries({ queryKey: ['chapterProgress', chapterId] })
      setIsEditDialogOpen(false)
      setEditingSubChapter(null)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteSubChapter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
      queryClient.invalidateQueries({ queryKey: ['chapterProgress', chapterId] })
      setIsDeleteDialogOpen(false)
      setDeletingSubChapter(null)
    },
  })

  // Reorder mutation with optimistic updates
  const reorderMutation = useMutation({
    mutationFn: ({ subChapterId, newPosition }: { subChapterId: string; newPosition: number }) =>
      reorderSubChapter(subChapterId, newPosition),
    // Optimistic update - update UI immediately before server responds
    onMutate: async ({ subChapterId, newPosition }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['subChapters', chapterId] })

      // Snapshot the previous value
      const previousSubChapters = queryClient.getQueryData(['subChapters', chapterId])

      // Optimistically update the cache
      queryClient.setQueryData(['subChapters', chapterId], (old: any) => {
        if (!old) return old
        const subChaptersList = Array.isArray(old) ? old : old.subChapters || []
        const chapters = [...subChaptersList]
        const oldIndex = chapters.findIndex((sc: SubChapter) => sc.id === subChapterId)
        const newIndex = newPosition - 1

        if (oldIndex !== -1 && newIndex >= 0 && newIndex < chapters.length) {
          const reordered = arrayMove(chapters, oldIndex, newIndex)
          // Update sub-chapter numbers
          reordered.forEach((sc: SubChapter, idx: number) => {
            sc.sub_chapter_number = idx + 1
          })
          return Array.isArray(old) ? reordered : { ...old, subChapters: reordered }
        }
        return old
      })

      return { previousSubChapters }
    },
    // If mutation fails, roll back to previous value
    onError: (_err, _variables, context) => {
      if (context?.previousSubChapters) {
        queryClient.setQueryData(['subChapters', chapterId], context.previousSubChapters)
      }
    },
    // Always refetch after error or success to ensure sync with server
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
    },
  })

  // Regenerate mutation
  const regenerateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SubChapterRegenerateRequest }) =>
      regenerateSubChapter(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
      queryClient.invalidateQueries({ queryKey: ['chapterProgress', chapterId] })
      setIsRegenerateDialogOpen(false)
      setRegeneratingSubChapter(null)
    },
  })

  // Resolve flag mutation
  const resolveFlagMutation = useMutation({
    mutationFn: (flagId: string) => resolveContentReviewFlag(flagId, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapterFlags', viewingFlagsSubChapter?.id] })
    },
  })

  // Update content mutation
  const updateContentMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSubChapterContentRequest }) =>
      updateSubChapterContent(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
      queryClient.invalidateQueries({ queryKey: ['chapterProgress', chapterId] })
      setIsEditingContent(false)
      setEditedContent('')
      setEditContentDescription('')
    },
  })

  const resetForm = () => {
    setFormData({
      title: '',
      plot_points: '',
      status: 'draft',
    })
  }

  const handleCreate = () => {
    const request: CreateSubChapterRequest = {
      chapter_id: chapterId!,
      title: formData.title || undefined,
      plot_points: formData.plot_points || undefined,
    }

    createMutation.mutate(request)
  }

  const handleEdit = () => {
    if (!editingSubChapter) return

    const data: UpdateSubChapterRequest = {
      title: formData.title || undefined,
      plot_points: formData.plot_points || undefined,
      status: formData.status,
    }

    updateMutation.mutate({
      id: editingSubChapter.id,
      data,
    })
  }

  const openEditDialog = (subChapter: SubChapter) => {
    setEditingSubChapter(subChapter)
    setFormData({
      title: subChapter.title || '',
      plot_points: subChapter.plot_points || '',
      status: subChapter.status,
    })
    setIsEditDialogOpen(true)
  }

  const openDeleteDialog = (subChapter: SubChapter) => {
    setDeletingSubChapter(subChapter)
    setIsDeleteDialogOpen(true)
  }

  const openRegenerateDialog = (subChapter: SubChapter) => {
    setRegeneratingSubChapter(subChapter)
    setIsRegenerateDialogOpen(true)
  }

  const openVersionsDialog = (subChapter: SubChapter) => {
    setViewingVersionsSubChapter(subChapter)
    setIsVersionsDialogOpen(true)
  }

  const openFlagsDialog = (subChapter: SubChapter) => {
    setViewingFlagsSubChapter(subChapter)
    setIsFlagsDialogOpen(true)
  }

  const openContentDialog = (subChapter: SubChapter) => {
    setViewingContentSubChapter(subChapter)
    setIsContentDialogOpen(true)
    setIsEditingContent(false)
    setEditedContent('')
    setEditContentDescription('')
  }

  // Handle query parameter to auto-open content dialog
  useEffect(() => {
    const viewSubChapterId = searchParams.get('viewSubChapter')
    if (viewSubChapterId && subChapters.length > 0) {
      const subChapter = subChapters.find((sc) => sc.id === viewSubChapterId)
      if (subChapter) {
        openContentDialog(subChapter)
        // Remove the query parameter after opening
        searchParams.delete('viewSubChapter')
        setSearchParams(searchParams, { replace: true })
      }
    }
  }, [searchParams, subChapters])

  const handleStartEditingContent = () => {
    if (viewingContentSubChapter?.content) {
      setEditedContent(viewingContentSubChapter.content)
      setIsEditingContent(true)
    }
  }

  const handleSaveContent = () => {
    if (!viewingContentSubChapter) return

    updateContentMutation.mutate({
      id: viewingContentSubChapter.id,
      data: {
        content: editedContent,
        change_description: editContentDescription || undefined,
      },
    })
  }

  const handleCancelEditingContent = () => {
    setIsEditingContent(false)
    setEditedContent('')
    setEditContentDescription('')
  }

  const calculateProgress = (subChapter: SubChapter) => {
    // Default target is 250 words if not specified elsewhere
    const targetWordCount = 250

    const percentage = (subChapter.word_count / targetWordCount) * 100
    let status: 'not_started' | 'in_progress' | 'near_complete' | 'complete' = 'not_started'

    if (subChapter.word_count === 0) {
      status = 'not_started'
    } else if (percentage >= 100) {
      status = 'complete'
    } else if (percentage >= 80) {
      status = 'near_complete'
    } else {
      status = 'in_progress'
    }

    return { percentage: Math.min(percentage, 100), status }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-success text-success-foreground'
      case 'in_progress':
        return 'bg-accent text-accent-foreground'
      case 'needs_review':
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

  // Filter sub-chapters based on search query
  const filteredSubChapters = useMemo(() => {
    if (!searchQuery.trim()) return subChapters
    const query = searchQuery.toLowerCase()
    return subChapters.filter(
      (sc) =>
        sc.title?.toLowerCase().includes(query) ||
        sc.plot_points?.toLowerCase().includes(query) ||
        sc.content?.toLowerCase().includes(query)
    )
  }, [subChapters, searchQuery])

  // Get flag count for a sub-chapter
  const getFlagCount = (_subChapterId: string) => {
    // This would ideally be fetched per sub-chapter, but for now we'll return 0
    // In a full implementation, you'd fetch flags for each sub-chapter
    return 0
  }

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

    const oldIndex = subChapters.findIndex((sc) => sc.id === active.id)
    const newIndex = subChapters.findIndex((sc) => sc.id === targetId)

    if (oldIndex !== -1 && newIndex !== -1) {
      const newPosition = newIndex + 1

      reorderMutation.mutate({
        subChapterId: active.id as string,
        newPosition,
      })
    }
  }

  if (subChaptersLoading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-8">
        <p className="text-muted-foreground">Loading sub-chapters...</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      {/* Header Row */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back
        </Button>
        <Button
          size="sm"
          onClick={() => setIsCreateDialogOpen(true)}
        >
          <Plus className="mr-1 h-4 w-4" />
          Add Sub-Chapter
        </Button>
      </div>

      {/* Title & Progress Section */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            {chapter && (
              <>
                <h1 className="text-2xl font-semibold text-foreground">Chapter {chapter.chapter_number}: {chapter.title}</h1>
                {chapter.chapter_plot && (
                  <p className="text-sm text-muted-foreground/80 mt-2 italic max-w-2xl">
                    {chapter.chapter_plot}
                  </p>
                )}
              </>
            )}
            <p className="text-sm text-muted-foreground mt-1">
              Sub-Chapters
            </p>
          </div>
        </div>

        {/* Compact Progress Summary */}
        {progressData && (
          <div className="mt-4 p-4 bg-muted/30 rounded border border-border">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">
                  {progressData.total_sub_chapters || 0} sub-chapters
                </span>
                <span className="text-border">•</span>
                <span className="text-muted-foreground">
                  {progressData.sub_chapters_completed || 0} completed
                </span>
                <span className="text-border">•</span>
                <span className="text-muted-foreground">
                  {(progressData.total_word_count || 0).toLocaleString()} / {(progressData.total_target_word_count || 0).toLocaleString()} words
                </span>
              </div>
              <span className="text-sm font-medium">{(progressData.overall_percentage || 0).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
              <div
                className="h-1.5 rounded-full bg-primary transition-all"
                style={{ width: `${progressData.overall_percentage || 0}%` }}
              />
            </div>
            {progressData.sub_chapters_by_status && (
              <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                  {progressData.sub_chapters_by_status.draft || 0} Draft
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-accent" />
                  {progressData.sub_chapters_by_status.in_progress || 0} In Progress
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-success" />
                  {progressData.sub_chapters_by_status.completed || 0} Complete
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-warning" />
                  {progressData.sub_chapters_by_status.needs_review || 0} Needs Review
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Content Section */}
      <div>

      {/* Search and View Toggle */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sub-chapters by title, plot points, or content..."
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

      {/* Sub-Chapters List */}
      {subChapters.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No sub-chapters yet</h3>
            <p className="text-muted-foreground mb-4">
              Start writing by creating the first sub-chapter
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create First Sub-Chapter
            </Button>
          </CardContent>
        </Card>
      ) : filteredSubChapters.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No sub-chapters found</h3>
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
            items={filteredSubChapters.map((sc) => sc.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="border rounded divide-y">
              {filteredSubChapters.map((subChapter) => {
                const progress = calculateProgress(subChapter)
                return (
                  <SortableSubChapterListItem
                    key={subChapter.id}
                    subChapter={subChapter}
                    progress={progress}
                    getStatusColor={getStatusColor}
                    truncateText={truncateText}
                    onEdit={openEditDialog}
                    onDelete={openDeleteDialog}
                    onRegenerate={openRegenerateDialog}
                    onViewVersions={openVersionsDialog}
                    onViewFlags={openFlagsDialog}
                    onViewContent={openContentDialog}
                    flagCount={getFlagCount(subChapter.id)}
                    chapterId={chapterId}
                    queryClient={queryClient}
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
            items={filteredSubChapters.map((sc) => sc.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="grid gap-4">
              {filteredSubChapters.map((subChapter) => {
                const progress = calculateProgress(subChapter)
                return (
                  <SortableSubChapterCard
                    key={subChapter.id}
                    subChapter={subChapter}
                    progress={progress}
                    getStatusColor={getStatusColor}
                    onEdit={openEditDialog}
                    onDelete={openDeleteDialog}
                    onRegenerate={openRegenerateDialog}
                    onViewVersions={openVersionsDialog}
                    onViewFlags={openFlagsDialog}
                    onViewContent={openContentDialog}
                    flagCount={getFlagCount(subChapter.id)}
                    chapterId={chapterId}
                    queryClient={queryClient}
                  />
                )
              })}
            </div>
          </SortableContext>
        </DndContext>
      )}
      </div>

      {/* Create Sub-Chapter Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Sub-Chapter</DialogTitle>
            <DialogDescription>
              Add a new sub-chapter to this chapter. Content will be generated if you provide plot points.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">Title (Optional)</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g., The Discovery"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="plot_points">Plot Points</Label>
              <Textarea
                id="plot_points"
                value={formData.plot_points}
                onChange={(e) => setFormData({ ...formData, plot_points: e.target.value })}
                placeholder="Describe what happens in this sub-chapter..."
                rows={4}
              />
              <p className="text-xs text-muted-foreground">
                Target: ~2000 words per sub-chapter
              </p>
            </div>
          </div>
          <DialogFooter className="flex flex-row justify-between items-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (formData.plot_points && chapter) {
                  setIsRulePreviewDialogOpen(true)
                }
              }}
              disabled={!formData.plot_points || !chapter}
              className="mr-auto"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Preview Rules
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Sub-Chapter'}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Sub-Chapter Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Sub-Chapter</DialogTitle>
            <DialogDescription>
              Update the title, plot points, or status for this sub-chapter.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-title">Title</Label>
              <Input
                id="edit-title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-plot_points">Plot Points</Label>
              <Textarea
                id="edit-plot_points"
                value={formData.plot_points}
                onChange={(e) => setFormData({ ...formData, plot_points: e.target.value })}
                rows={4}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-status">Status</Label>
              <Select
                value={formData.status}
                onValueChange={(value: any) => setFormData({ ...formData, status: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="needs_review">Needs Review</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setIsRulePreviewDialogOpen(true)
              }}
              disabled={!formData.plot_points || !chapter}
              className="mr-auto"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Preview Rules
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleEdit}
                disabled={updateMutation.isPending}
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
            <DialogTitle>Delete Sub-Chapter</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete sub-chapter {deletingSubChapter?.sub_chapter_number}?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deletingSubChapter && deleteMutation.mutate(deletingSubChapter.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate Dialog */}
      <Dialog open={isRegenerateDialogOpen} onOpenChange={setIsRegenerateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Regenerate Content</DialogTitle>
            <DialogDescription>
              Regenerate the content for sub-chapter {regeneratingSubChapter?.sub_chapter_number}.
              This will create a new version.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRegenerateDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => regeneratingSubChapter && regenerateMutation.mutate({
                id: regeneratingSubChapter.id,
                data: {}
              })}
              disabled={regenerateMutation.isPending}
            >
              {regenerateMutation.isPending ? 'Regenerating...' : 'Regenerate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Version History Dialog - Epic 7 */}
      {viewingVersionsSubChapter && (
        <VersionHistoryDialog
          subChapterId={viewingVersionsSubChapter.id}
          subChapterTitle={viewingVersionsSubChapter.title}
          open={isVersionsDialogOpen}
          onOpenChange={setIsVersionsDialogOpen}
          onVersionRestored={() => {
            queryClient.invalidateQueries({ queryKey: ['subChapters', chapterId] })
          }}
        />
      )}

      {/* Review Flags Dialog */}
      <Dialog open={isFlagsDialogOpen} onOpenChange={setIsFlagsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Content Review Flags</DialogTitle>
            <DialogDescription>
              Review and resolve content flags for this sub-chapter.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {flags.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No review flags for this sub-chapter.
              </p>
            ) : (
              flags.map((flag) => (
                <Card key={flag.id} className={flag.resolved_at ? 'opacity-60' : ''}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={flag.resolved_at ? 'secondary' : 'destructive'}>
                            {flag.flag_type.replace('_', ' ')}
                          </Badge>
                          {flag.resolved_at && <span className="text-xs text-muted-foreground">Resolved</span>}
                        </div>
                        <p className="text-sm">{flag.description}</p>
                        {flag.old_value && flag.new_value && (
                          <div className="mt-2 text-xs space-y-1">
                            <p><span className="font-semibold">Old:</span> {flag.old_value}</p>
                            <p><span className="font-semibold">New:</span> {flag.new_value}</p>
                          </div>
                        )}
                      </div>
                      {!flag.resolved_at && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => resolveFlagMutation.mutate(flag.id)}
                          disabled={resolveFlagMutation.isPending}
                        >
                          Resolve
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                </Card>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* View Content Dialog */}
      <Dialog open={isContentDialogOpen} onOpenChange={setIsContentDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle>
                  {viewingContentSubChapter?.title || `Sub-Chapter ${viewingContentSubChapter?.sub_chapter_number}`}
                </DialogTitle>
                <DialogDescription>
                  {isEditingContent
                    ? `${editedContent.split(/\s+/).filter(w => w.length > 0).length.toLocaleString()} words`
                    : `${viewingContentSubChapter?.word_count.toLocaleString()} words`
                  }
                </DialogDescription>
              </div>
              {!isEditingContent && viewingContentSubChapter?.content && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      setEditedContent(viewingContentSubChapter.content || '')
                      setIsZenModeOpen(true)
                    }}
                    title="Focus mode"
                    className="transition-smooth"
                  >
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleStartEditingContent}
                    title="Edit content"
                    className="transition-smooth"
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          </DialogHeader>
          <div className="py-4">
            {viewingContentSubChapter?.content ? (
              isEditingContent ? (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="edit-description" className="text-sm font-medium">
                      Description of Changes (Optional)
                    </Label>
                    <Input
                      id="edit-description"
                      value={editContentDescription}
                      onChange={(e) => setEditContentDescription(e.target.value)}
                      placeholder="e.g., Fixed typos, improved dialogue flow"
                      className="mt-2"
                      maxLength={1000}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {editContentDescription.length}/1000 characters
                    </p>
                  </div>
                  <Textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="min-h-[400px] font-sans text-sm leading-relaxed"
                    placeholder="Edit your content here..."
                  />
                </div>
              ) : (
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                    {viewingContentSubChapter.content}
                  </pre>
                </div>
              )
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No content generated yet.
              </p>
            )}
          </div>
          <DialogFooter>
            {isEditingContent ? (
              <>
                <Button
                  variant="outline"
                  onClick={handleCancelEditingContent}
                  disabled={updateContentMutation.isPending}
                >
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveContent}
                  disabled={updateContentMutation.isPending || !editedContent.trim()}
                >
                  <Save className="mr-2 h-4 w-4" />
                  {updateContentMutation.isPending ? 'Saving...' : 'Save'}
                </Button>
              </>
            ) : (
              <Button variant="outline" onClick={() => setIsContentDialogOpen(false)}>
                Close
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rule Preview Dialog (Epic 5B) */}
      <RulePreviewDialog
        open={isRulePreviewDialogOpen}
        onOpenChange={setIsRulePreviewDialogOpen}
        previewParams={
          formData.plot_points && chapter && book
            ? {
                prompt: formData.title || 'Generate content for this sub-chapter',
                plot_points: formData.plot_points,
                book_id: chapter.book_id,
                trilogy_id: book.trilogy_id,
                max_rules: 10,
                similarity_threshold: 0.1,
              }
            : null
        }
        onConfirm={() => {
          // If we're in Create mode, create the sub-chapter
          // If we're in Edit mode, just close the preview
          if (isCreateDialogOpen) {
            handleCreate()
          } else {
            setIsRulePreviewDialogOpen(false)
          }
        }}
      />

      {/* Zen Mode - Distraction-free writing */}
      <ZenMode
        isOpen={isZenModeOpen}
        onClose={() => {
          setIsZenModeOpen(false)
          // If content was edited in zen mode, update it
          if (editedContent !== viewingContentSubChapter?.content) {
            setIsEditingContent(true)
          }
        }}
        content={editedContent}
        onContentChange={setEditedContent}
        placeholder="Begin writing..."
      />
    </div>
  )
}
