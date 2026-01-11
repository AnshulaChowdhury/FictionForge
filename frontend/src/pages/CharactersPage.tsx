/**
 * Characters page for managing trilogy characters (Epic 2).
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { getTrilogyCharacters, createCharacter, updateCharacter, deleteCharacter, GENDER_LABELS } from '@/api/characters'
import type { Character, CharacterTraits, Gender } from '@/api/characters'
import { getTrilogy, getTrilogyBooks } from '@/api/trilogy'
import type { Book } from '@/api/trilogy'
import { ArrowLeft, Plus, UserPlus, Edit, Trash2, User, Search, LayoutGrid, List } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

type ViewMode = 'list' | 'card'

export function CharactersPage() {
  const { trilogyId } = useParams<{ trilogyId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [deletingCharacter, setDeletingCharacter] = useState<Character | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('list')

  const [formData, setFormData] = useState<{
    name: string
    gender: Gender | ''
    description: string
    character_arc: string
    personality: string
    speech_patterns: string
    physical_description: string
    background: string
    motivations: string
    selectedBookIds: string[]
  }>({
    name: '',
    gender: '',
    description: '',
    character_arc: '',
    personality: '',
    speech_patterns: '',
    physical_description: '',
    background: '',
    motivations: '',
    selectedBookIds: [],
  })

  const { data: trilogy } = useQuery({
    queryKey: ['trilogy', trilogyId],
    queryFn: () => getTrilogy(trilogyId!),
    enabled: !!trilogyId,
  })

  const { data: books = [] } = useQuery({
    queryKey: ['books', trilogyId],
    queryFn: () => getTrilogyBooks(trilogyId!),
    enabled: !!trilogyId,
  })

  const { data: charactersData, isLoading } = useQuery({
    queryKey: ['characters', trilogyId],
    queryFn: () => getTrilogyCharacters(trilogyId!),
    enabled: !!trilogyId,
  })

  const createMutation = useMutation({
    mutationFn: createCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', trilogyId] })
      setIsCreateDialogOpen(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      updateCharacter(id, data),
    onSuccess: async () => {
      // Wait for the query to refetch before closing the dialog
      // This ensures the list has fresh data when user reopens the dialog
      await queryClient.invalidateQueries({ queryKey: ['characters', trilogyId] })
      setIsEditDialogOpen(false)
      setEditingCharacter(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', trilogyId] })
      setIsDeleteDialogOpen(false)
      setDeletingCharacter(null)
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      gender: '',
      description: '',
      character_arc: '',
      personality: '',
      speech_patterns: '',
      physical_description: '',
      background: '',
      motivations: '',
      selectedBookIds: [],
    })
  }

  const toggleBookSelection = (bookId: string) => {
    setFormData((prev) => ({
      ...prev,
      selectedBookIds: prev.selectedBookIds.includes(bookId)
        ? prev.selectedBookIds.filter((id) => id !== bookId)
        : [...prev.selectedBookIds, bookId],
    }))
  }

  const handleCreate = () => {
    const traits: CharacterTraits = {
      personality: formData.personality ? formData.personality.split(',').map(s => s.trim()).filter(Boolean) : [],
      speech_patterns: formData.speech_patterns ? formData.speech_patterns.split(',').map(s => s.trim()).filter(Boolean) : [],
      physical_description: formData.physical_description || undefined,
      background: formData.background || undefined,
      motivations: formData.motivations ? formData.motivations.split(',').map(s => s.trim()).filter(Boolean) : [],
    }

    createMutation.mutate({
      trilogy_id: trilogyId!,
      name: formData.name,
      gender: formData.gender || undefined,
      description: formData.description || undefined,
      traits,
      character_arc: formData.character_arc || undefined,
      book_ids: formData.selectedBookIds,
    })
  }

  const handleEdit = () => {
    if (!editingCharacter) return

    const traits: CharacterTraits = {
      personality: formData.personality ? formData.personality.split(',').map(s => s.trim()).filter(Boolean) : [],
      speech_patterns: formData.speech_patterns ? formData.speech_patterns.split(',').map(s => s.trim()).filter(Boolean) : [],
      physical_description: formData.physical_description || undefined,
      background: formData.background || undefined,
      motivations: formData.motivations ? formData.motivations.split(',').map(s => s.trim()).filter(Boolean) : [],
    }

    updateMutation.mutate({
      id: editingCharacter.id,
      data: {
        name: formData.name,
        gender: formData.gender || undefined,
        description: formData.description || undefined,
        traits,
        character_arc: formData.character_arc || undefined,
        book_ids: formData.selectedBookIds,
      },
    })
  }

  const openEditDialog = (character: Character) => {
    setEditingCharacter(character)
    setFormData({
      name: character.name,
      gender: character.gender || '',
      description: character.description || '',
      character_arc: character.character_arc || '',
      personality: character.traits?.personality?.join(', ') || '',
      speech_patterns: character.traits?.speech_patterns?.join(', ') || '',
      physical_description: character.traits?.physical_description || '',
      background: character.traits?.background || '',
      motivations: character.traits?.motivations?.join(', ') || '',
      selectedBookIds: character.book_ids || [],
    })
    setIsEditDialogOpen(true)
  }

  const openDeleteDialog = (character: Character) => {
    setDeletingCharacter(character)
    setIsDeleteDialogOpen(true)
  }

  // Filter characters by search
  const filteredCharacters = useMemo(() => {
    if (!charactersData?.characters) return []
    if (!searchQuery.trim()) return charactersData.characters

    const query = searchQuery.toLowerCase()
    return charactersData.characters.filter(
      (char) =>
        char.name.toLowerCase().includes(query) ||
        char.description?.toLowerCase().includes(query) ||
        char.character_arc?.toLowerCase().includes(query)
    )
  }, [charactersData?.characters, searchQuery])

  // Truncate description for excerpt
  const truncateText = (text: string | undefined, maxLength: number = 120) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength).trim() + '...'
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-muted-foreground">Loading characters...</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      <Button
        variant="ghost"
        onClick={() => navigate(`/trilogy/${trilogyId}`)}
        className="mb-6"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Trilogy
      </Button>

      <div className="flex items-center justify-between mb-6 mx-6">
        <div>
          <h1 className="text-2xl font-semibold">Characters</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {trilogy?.title}
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <UserPlus className="w-4 h-4 mr-2" />
          Create Character
        </Button>
      </div>

      {/* Search and View Toggle */}
      <div className="flex items-center gap-3 mb-6 mx-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search characters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex border rounded overflow-hidden">
          <button
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

      {charactersData?.total === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <User className="w-12 h-12 text-muted-foreground mb-4" />
            <p className="text-base font-medium mb-2">No characters yet</p>
            <p className="text-muted-foreground text-sm text-center mb-6">
              Create your first character to start building your cast.
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Character
            </Button>
          </CardContent>
        </Card>
      ) : filteredCharacters.length === 0 ? (
        <div className="text-center py-12 bg-muted rounded">
          <p className="text-muted-foreground">No characters match your search.</p>
        </div>
      ) : viewMode === 'list' ? (
        /* List View */
        <div className="border rounded divide-y mx-6">
          {filteredCharacters.map((character) => (
            <div
              key={character.id}
              className="flex items-start gap-4 p-4 hover:bg-muted/50 transition-colors cursor-pointer"
              onClick={() => openEditDialog(character)}
              onDoubleClick={() => openEditDialog(character)}
            >
              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="font-medium text-foreground">{character.name}</h3>
                    {character.description && (
                      <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                        {truncateText(character.description, 150)}
                      </p>
                    )}
                    {character.traits?.personality && character.traits.personality.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {character.traits.personality.slice(0, 4).map((trait, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">{trait}</Badge>
                        ))}
                        {character.traits.personality.length > 4 && (
                          <span className="text-xs text-muted-foreground">+{character.traits.personality.length - 4} more</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(character)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openDeleteDialog(character)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Card View */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCharacters.map((character) => (
            <Card
              key={character.id}
              className="hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => openEditDialog(character)}
              onDoubleClick={() => openEditDialog(character)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5 text-accent" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{character.name}</CardTitle>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(character)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openDeleteDialog(character)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {character.description && (
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {truncateText(character.description, 180)}
                  </p>
                )}
                {character.traits?.personality && character.traits.personality.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {character.traits.personality.slice(0, 5).map((trait, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">{trait}</Badge>
                    ))}
                    {character.traits.personality.length > 5 && (
                      <span className="text-xs text-muted-foreground self-center">+{character.traits.personality.length - 5}</span>
                    )}
                  </div>
                )}
                {character.character_arc && (
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Arc:</span> {truncateText(character.character_arc, 100)}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Character</DialogTitle>
            <DialogDescription>
              Add a new character to your trilogy.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Dr. Sarah Chen"
                />
              </div>
              <div>
                <Label htmlFor="gender">Gender</Label>
                <Select
                  value={formData.gender}
                  onValueChange={(value: Gender) => setFormData({ ...formData, gender: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(GENDER_LABELS) as Gender[]).map((key) => (
                      <SelectItem key={key} value={key}>
                        {GENDER_LABELS[key]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="A brilliant neuroscientist..."
                rows={3}
              />
            </div>
            <div>
              <Label htmlFor="personality">Personality Traits (comma-separated)</Label>
              <Input
                id="personality"
                value={formData.personality}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                placeholder="analytical, determined, empathetic"
              />
            </div>
            <div>
              <Label htmlFor="speech_patterns">Speech Patterns (comma-separated)</Label>
              <Input
                id="speech_patterns"
                value={formData.speech_patterns}
                onChange={(e) => setFormData({ ...formData, speech_patterns: e.target.value })}
                placeholder="uses scientific terminology, speaks precisely"
              />
            </div>
            <div>
              <Label htmlFor="physical_description">Physical Description</Label>
              <Textarea
                id="physical_description"
                value={formData.physical_description}
                onChange={(e) => setFormData({ ...formData, physical_description: e.target.value })}
                placeholder="Tall with short dark hair and piercing blue eyes"
                rows={2}
              />
            </div>
            <div>
              <Label htmlFor="background">Background</Label>
              <Textarea
                id="background"
                value={formData.background}
                onChange={(e) => setFormData({ ...formData, background: e.target.value })}
                placeholder="Former MIT neuroscientist who lost their partner in an AI accident"
                rows={2}
              />
            </div>
            <div>
              <Label htmlFor="motivations">Motivations (comma-separated)</Label>
              <Input
                id="motivations"
                value={formData.motivations}
                onChange={(e) => setFormData({ ...formData, motivations: e.target.value })}
                placeholder="understand consciousness, prevent AI suffering, find redemption"
              />
            </div>
            <div>
              <Label htmlFor="character_arc">Character Arc</Label>
              <Textarea
                id="character_arc"
                value={formData.character_arc}
                onChange={(e) => setFormData({ ...formData, character_arc: e.target.value })}
                placeholder="Begins as skeptical materialist, evolves to accept consciousness transcendence"
                rows={3}
              />
            </div>
            {/* Book Selection */}
            <div className="space-y-3">
              <Label>Appears in Books</Label>
              <p className="text-sm text-muted-foreground">
                Select which books this character appears in.
              </p>
              <div className="space-y-2">
                {books.map((book) => (
                  <div key={book.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`create-book-${book.id}`}
                      checked={formData.selectedBookIds.includes(book.id)}
                      onCheckedChange={() => toggleBookSelection(book.id)}
                    />
                    <label
                      htmlFor={`create-book-${book.id}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      Book {book.book_number}: {book.title}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsCreateDialogOpen(false); resetForm() }}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={!formData.name || createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Character'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Character</DialogTitle>
            <DialogDescription>
              Update character details.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit-name">Name *</Label>
                <Input
                  id="edit-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="edit-gender">Gender</Label>
                <Select
                  value={formData.gender}
                  onValueChange={(value: Gender) => setFormData({ ...formData, gender: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(GENDER_LABELS) as Gender[]).map((key) => (
                      <SelectItem key={key} value={key}>
                        {GENDER_LABELS[key]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
            <div>
              <Label htmlFor="edit-personality">Personality Traits (comma-separated)</Label>
              <Input
                id="edit-personality"
                value={formData.personality}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="edit-speech_patterns">Speech Patterns (comma-separated)</Label>
              <Input
                id="edit-speech_patterns"
                value={formData.speech_patterns}
                onChange={(e) => setFormData({ ...formData, speech_patterns: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="edit-physical_description">Physical Description</Label>
              <Textarea
                id="edit-physical_description"
                value={formData.physical_description}
                onChange={(e) => setFormData({ ...formData, physical_description: e.target.value })}
                rows={2}
              />
            </div>
            <div>
              <Label htmlFor="edit-background">Background</Label>
              <Textarea
                id="edit-background"
                value={formData.background}
                onChange={(e) => setFormData({ ...formData, background: e.target.value })}
                rows={2}
              />
            </div>
            <div>
              <Label htmlFor="edit-motivations">Motivations (comma-separated)</Label>
              <Input
                id="edit-motivations"
                value={formData.motivations}
                onChange={(e) => setFormData({ ...formData, motivations: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="edit-character_arc">Character Arc</Label>
              <Textarea
                id="edit-character_arc"
                value={formData.character_arc}
                onChange={(e) => setFormData({ ...formData, character_arc: e.target.value })}
                rows={3}
              />
            </div>
            {/* Book Selection */}
            <div className="space-y-3">
              <Label>Appears in Books</Label>
              <p className="text-sm text-muted-foreground">
                Select which books this character appears in.
              </p>
              <div className="space-y-2">
                {books.map((book) => (
                  <div key={book.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`edit-book-${book.id}`}
                      checked={formData.selectedBookIds.includes(book.id)}
                      onCheckedChange={() => toggleBookSelection(book.id)}
                    />
                    <label
                      htmlFor={`edit-book-${book.id}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      Book {book.book_number}: {book.title}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsEditDialogOpen(false); setEditingCharacter(null); resetForm() }}>
              Cancel
            </Button>
            <Button onClick={handleEdit} disabled={!formData.name || updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Character</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingCharacter?.name}"? This action cannot be undone and will remove all associated chapters.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsDeleteDialogOpen(false); setDeletingCharacter(null) }}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deletingCharacter && deleteMutation.mutate(deletingCharacter.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
