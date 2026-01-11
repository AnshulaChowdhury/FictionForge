/**
 * Epic 7: Version Control & Content Management
 *
 * Comprehensive version history dialog with:
 * - Story 1: Display all versions with metadata
 * - Story 2: Restore previous versions with confirmation
 * - Story 3: Inline description editing
 * - Story 4: Sorting, filtering, and metadata tracking
 * - CRITICAL: Side-by-side version comparison
 */

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  History,
  RotateCcw,
  Edit,
  Save,
  X,
  Search,
  Filter,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Eye,
  GitCompare,
  Sparkles,
  FileText,
  Calendar,
  Hash,
  User
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { supabase } from '@/lib/supabase'
import {
  getSubChapterVersions,
  getSubChapterVersion,
  restoreSubChapterVersion,
  updateVersionDescription,
} from '@/api/subChapters'
import type {
  SubChapterVersion,
  SubChapterVersionListItem,
} from '@/api/subChapters'

interface VersionHistoryDialogProps {
  subChapterId: string
  subChapterTitle?: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onVersionRestored?: () => void
}

type SortField = 'version_number' | 'created_at' | 'word_count'
type SortOrder = 'asc' | 'desc'

interface FilterState {
  aiGenerated?: boolean
  searchQuery: string
}

export function VersionHistoryDialog({
  subChapterId,
  subChapterTitle,
  open,
  onOpenChange,
  onVersionRestored,
}: VersionHistoryDialogProps) {
  const queryClient = useQueryClient()

  // State
  const [sortField, setSortField] = useState<SortField>('version_number')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [filter, setFilter] = useState<FilterState>({ searchQuery: '' })
  const [editingVersionId, setEditingVersionId] = useState<string | null>(null)
  const [editDescription, setEditDescription] = useState('')
  const [restoreVersionId, setRestoreVersionId] = useState<string | null>(null)
  const [compareVersionIds, setCompareVersionIds] = useState<[string | null, string | null]>([null, null])
  const [showComparison, setShowComparison] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Fetch versions
  const { data: versions = [], isLoading } = useQuery({
    queryKey: ['subChapterVersions', subChapterId],
    queryFn: () => getSubChapterVersions(subChapterId),
    enabled: open,
  })

  // Fetch full versions for comparison
  const { data: version1 } = useQuery({
    queryKey: ['subChapterVersion', compareVersionIds[0]],
    queryFn: () => getSubChapterVersion(compareVersionIds[0]!),
    enabled: !!compareVersionIds[0] && showComparison,
  })

  const { data: version2 } = useQuery({
    queryKey: ['subChapterVersion', compareVersionIds[1]],
    queryFn: () => getSubChapterVersion(compareVersionIds[1]!),
    enabled: !!compareVersionIds[1] && showComparison,
  })

  // Update description mutation
  const updateDescriptionMutation = useMutation({
    mutationFn: ({ versionId, description }: { versionId: string; description: string }) =>
      updateVersionDescription(versionId, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapterVersions', subChapterId] })
      setSuccessMessage('Version description saved successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
      setEditingVersionId(null)
      setEditDescription('')
    },
    onError: (error: any) => {
      alert(error.response?.data?.message || 'Failed to update description')
    },
  })

  // Restore version mutation
  const restoreVersionMutation = useMutation({
    mutationFn: (versionId: string) => restoreSubChapterVersion(versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subChapterVersions', subChapterId] })
      queryClient.invalidateQueries({ queryKey: ['subChapters'] })
      setSuccessMessage('Sub-chapter content has been restored to the selected version')
      setTimeout(() => setSuccessMessage(null), 3000)
      setRestoreVersionId(null)
      onVersionRestored?.()
    },
    onError: (error: any) => {
      alert(error.response?.data?.message || 'Failed to restore version')
    },
  })

  // Realtime subscription for version updates
  useEffect(() => {
    if (!open || !subChapterId) return

    const channel = supabase
      .channel(`sub_chapter_versions:${subChapterId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'sub_chapter_versions',
          filter: `sub_chapter_id=eq.${subChapterId}`,
        },
        (payload) => {
          // New version created
          queryClient.invalidateQueries({ queryKey: ['subChapterVersions', subChapterId] })
          setSuccessMessage(`Version ${payload.new.version_number} has been generated`)
          setTimeout(() => setSuccessMessage(null), 3000)
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'sub_chapter_versions',
          filter: `sub_chapter_id=eq.${subChapterId}`,
        },
        (payload) => {
          // Version description updated
          queryClient.invalidateQueries({ queryKey: ['subChapterVersions', subChapterId] })
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [open, subChapterId, queryClient])

  // Sorting and filtering
  const filteredAndSortedVersions = useCallback(() => {
    let result = [...versions]

    // Apply filters
    if (filter.aiGenerated !== undefined) {
      result = result.filter((v) => v.is_ai_generated === filter.aiGenerated)
    }

    if (filter.searchQuery) {
      const query = filter.searchQuery.toLowerCase()
      result = result.filter(
        (v) =>
          v.change_description?.toLowerCase().includes(query) ||
          v.version_number.toString().includes(query)
      )
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal: any
      let bVal: any

      switch (sortField) {
        case 'version_number':
          aVal = a.version_number
          bVal = b.version_number
          break
        case 'created_at':
          aVal = new Date(a.created_at).getTime()
          bVal = new Date(b.created_at).getTime()
          break
        case 'word_count':
          aVal = a.word_count
          bVal = b.word_count
          break
      }

      if (sortOrder === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0
      }
    })

    return result
  }, [versions, filter, sortField, sortOrder])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const handleEditDescription = (version: SubChapterVersionListItem) => {
    setEditingVersionId(version.id)
    setEditDescription(version.change_description || '')
  }

  const handleSaveDescription = () => {
    if (!editingVersionId) return

    updateDescriptionMutation.mutate({
      versionId: editingVersionId,
      description: editDescription,
    })
  }

  const handleCancelEdit = () => {
    setEditingVersionId(null)
    setEditDescription('')
  }

  const handleRestore = (versionId: string) => {
    setRestoreVersionId(versionId)
  }

  const confirmRestore = () => {
    if (restoreVersionId) {
      restoreVersionMutation.mutate(restoreVersionId)
    }
  }

  const handleCompare = (version1Id: string, version2Id: string) => {
    setCompareVersionIds([version1Id, version2Id])
    setShowComparison(true)
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-4 w-4 ml-2 inline" />
    return sortOrder === 'asc' ? (
      <ArrowUp className="h-4 w-4 ml-2 inline" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-2 inline" />
    )
  }

  return (
    <>
      <Dialog open={open && !showComparison} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-6xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Version History
              {subChapterTitle && ` - ${subChapterTitle}`}
            </DialogTitle>
            <DialogDescription>
              View, compare, and restore previous versions of this sub-chapter. All versions are preserved.
            </DialogDescription>
          </DialogHeader>

          {/* Success Message */}
          {successMessage && (
            <Alert className="bg-green-50 border-green-200">
              <AlertDescription className="text-green-800">
                {successMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* Filters and Search */}
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search descriptions or version number..."
                  className="pl-8"
                  value={filter.searchQuery}
                  onChange={(e) => setFilter({ ...filter, searchQuery: e.target.value })}
                />
              </div>
            </div>

            <div className="w-[180px]">
              <Label htmlFor="filter-type">Filter by Type</Label>
              <Select
                value={filter.aiGenerated === undefined ? 'all' : filter.aiGenerated ? 'ai' : 'manual'}
                onValueChange={(value) =>
                  setFilter({
                    ...filter,
                    aiGenerated: value === 'all' ? undefined : value === 'ai',
                  })
                }
              >
                <SelectTrigger id="filter-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Versions</SelectItem>
                  <SelectItem value="ai">AI Generated</SelectItem>
                  <SelectItem value="manual">Manual Edits</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              onClick={() => setFilter({ searchQuery: '', aiGenerated: undefined })}
              disabled={!filter.searchQuery && filter.aiGenerated === undefined}
            >
              <X className="h-4 w-4 mr-2" />
              Clear Filters
            </Button>
          </div>

          <Separator />

          {/* Version Table */}
          <ScrollArea className="h-[400px] border rounded-md">
            {isLoading ? (
              <div className="p-8 text-center text-muted-foreground">Loading versions...</div>
            ) : filteredAndSortedVersions().length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                {versions.length === 0 ? 'No versions found' : 'No versions match your filters'}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[80px] cursor-pointer" onClick={() => handleSort('version_number')}>
                      <div className="flex items-center">
                        Version
                        <SortIcon field="version_number" />
                      </div>
                    </TableHead>
                    <TableHead className="w-[180px] cursor-pointer" onClick={() => handleSort('created_at')}>
                      <div className="flex items-center">
                        Created
                        <SortIcon field="created_at" />
                      </div>
                    </TableHead>
                    <TableHead className="w-[100px] cursor-pointer" onClick={() => handleSort('word_count')}>
                      <div className="flex items-center">
                        Words
                        <SortIcon field="word_count" />
                      </div>
                    </TableHead>
                    <TableHead className="w-[80px]">Type</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-[200px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedVersions().map((version) => (
                    <TableRow key={version.id} className={version.is_current ? 'bg-muted/50' : ''}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          v{version.version_number}
                          {version.is_current && (
                            <Badge variant="default" className="text-xs">
                              Current
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(version.created_at), 'MMM d, yyyy h:mm a')}
                      </TableCell>
                      <TableCell>{version.word_count.toLocaleString()}</TableCell>
                      <TableCell>
                        {version.is_ai_generated ? (
                          <Badge variant="secondary" className="gap-1">
                            <Sparkles className="h-3 w-3" />
                            AI
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="gap-1">
                            <FileText className="h-3 w-3" />
                            Manual
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {editingVersionId === version.id ? (
                          <div className="space-y-2">
                            <Textarea
                              value={editDescription}
                              onChange={(e) => setEditDescription(e.target.value)}
                              placeholder="Describe this version..."
                              maxLength={1000}
                              rows={2}
                              className="w-full"
                            />
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                              <span>{editDescription.length}/1000 characters</span>
                              <div className="flex gap-2">
                                <Button size="sm" onClick={handleSaveDescription} disabled={updateDescriptionMutation.isPending}>
                                  <Save className="h-3 w-3 mr-1" />
                                  Save
                                </Button>
                                <Button size="sm" variant="outline" onClick={handleCancelEdit}>
                                  <X className="h-3 w-3 mr-1" />
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-start justify-between group">
                            <span className="text-sm text-muted-foreground truncate flex-1">
                              {version.change_description || <em>No description</em>}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={() => handleEditDescription(version)}
                            >
                              <Edit className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          {!version.is_current && (
                            <Button variant="outline" size="sm" onClick={() => handleRestore(version.id)}>
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Restore
                            </Button>
                          )}
                          {versions.length > 1 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                const otherVersion = versions.find((v) => v.id !== version.id && v.is_current)
                                if (otherVersion) {
                                  handleCompare(version.id, otherVersion.id)
                                }
                              }}
                            >
                              <GitCompare className="h-3 w-3 mr-1" />
                              Compare
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </ScrollArea>

          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Total: {versions.length} version(s)</span>
            <span>Showing: {filteredAndSortedVersions().length} version(s)</span>
          </div>
        </DialogContent>
      </Dialog>

      {/* Restore Confirmation Dialog */}
      <AlertDialog open={!!restoreVersionId} onOpenChange={() => setRestoreVersionId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Previous Version?</AlertDialogTitle>
            <AlertDialogDescription>
              This will replace the current content with the selected version. All versions will be preserved, so you can always revert this change.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmRestore} disabled={restoreVersionMutation.isPending}>
              <RotateCcw className="h-4 w-4 mr-2" />
              Restore Version
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Version Comparison Dialog */}
      {showComparison && version1 && version2 && (
        <Dialog open={showComparison} onOpenChange={setShowComparison}>
          <DialogContent className="max-w-[95vw] max-h-[95vh]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <GitCompare className="h-5 w-5" />
                Compare Versions
              </DialogTitle>
              <DialogDescription>
                Side-by-side comparison of version {version1.version_number} and version {version2.version_number}
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-2 gap-4">
              {/* Version 1 */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                  <div>
                    <div className="font-semibold">Version {version1.version_number}</div>
                    <div className="text-sm text-muted-foreground">{format(new Date(version1.created_at), 'MMM d, yyyy h:mm a')}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">{version1.word_count.toLocaleString()} words</div>
                    {version1.is_ai_generated ? (
                      <Badge variant="secondary" className="gap-1 mt-1">
                        <Sparkles className="h-3 w-3" />
                        AI Generated
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1 mt-1">
                        <FileText className="h-3 w-3" />
                        Manual
                      </Badge>
                    )}
                  </div>
                </div>

                {version1.change_description && (
                  <div className="p-3 bg-muted/50 rounded-md">
                    <div className="text-xs font-medium text-muted-foreground mb-1">Description</div>
                    <div className="text-sm">{version1.change_description}</div>
                  </div>
                )}

                <Separator />

                <ScrollArea className="h-[500px] border rounded-md p-4">
                  <div className="prose prose-sm max-w-none whitespace-pre-wrap">{version1.content}</div>
                </ScrollArea>
              </div>

              {/* Version 2 */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                  <div>
                    <div className="font-semibold">Version {version2.version_number}</div>
                    <div className="text-sm text-muted-foreground">{format(new Date(version2.created_at), 'MMM d, yyyy h:mm a')}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">{version2.word_count.toLocaleString()} words</div>
                    {version2.is_ai_generated ? (
                      <Badge variant="secondary" className="gap-1 mt-1">
                        <Sparkles className="h-3 w-3" />
                        AI Generated
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1 mt-1">
                        <FileText className="h-3 w-3" />
                        Manual
                      </Badge>
                    )}
                  </div>
                </div>

                {version2.change_description && (
                  <div className="p-3 bg-muted/50 rounded-md">
                    <div className="text-xs font-medium text-muted-foreground mb-1">Description</div>
                    <div className="text-sm">{version2.change_description}</div>
                  </div>
                )}

                <Separator />

                <ScrollArea className="h-[500px] border rounded-md p-4">
                  <div className="prose prose-sm max-w-none whitespace-pre-wrap">{version2.content}</div>
                </ScrollArea>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowComparison(false)}>
                Close Comparison
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  )
}
