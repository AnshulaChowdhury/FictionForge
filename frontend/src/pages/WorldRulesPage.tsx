/**
 * WorldRulesPage Component (Epic 3)
 *
 * Main page for managing world rules.
 * Features: List, create, edit, delete, filter by category/book.
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  listWorldRules,
  createWorldRule,
  updateWorldRule,
  deleteWorldRule,
  getCategories,
} from '@/api/worldRules';
import type {
  WorldRule,
  CreateWorldRuleRequest,
  UpdateWorldRuleRequest,
} from '@/api/worldRules';
import { getTrilogyBooks } from '@/api/trilogy';
import { WorldRuleCard } from '@/components/world-rules/WorldRuleCard';
import { WorldRuleForm } from '@/components/world-rules/WorldRuleForm';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { Plus, Search, Filter, BookOpen, AlertCircle, BarChart3, ArrowLeft, LayoutGrid, List, Globe, Edit, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type ViewMode = 'list' | 'card';

export const WorldRulesPage: React.FC = () => {
  const { trilogyId } = useParams<{ trilogyId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedBookId, setSelectedBookId] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingRule, setEditingRule] = useState<WorldRule | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('card');

  if (!trilogyId) {
    return <Alert><AlertDescription>Trilogy ID is required</AlertDescription></Alert>;
  }

  // Queries
  const { data: rulesData, isLoading: rulesLoading, error: rulesError } = useQuery({
    queryKey: ['worldRules', trilogyId, selectedCategory, selectedBookId],
    queryFn: () => listWorldRules({
      trilogy_id: trilogyId,
      category: selectedCategory === 'all' ? undefined : selectedCategory,
      book_id: selectedBookId === 'all' ? undefined : selectedBookId,
    }),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['worldRuleCategories', trilogyId],
    queryFn: () => getCategories(trilogyId),
  });

  // Fetch books for this trilogy
  const { data: books = [] } = useQuery({
    queryKey: ['trilogyBooks', trilogyId],
    queryFn: () => getTrilogyBooks(trilogyId),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: createWorldRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['worldRules', trilogyId] });
      queryClient.invalidateQueries({ queryKey: ['worldRuleCategories', trilogyId] });
      setShowCreateDialog(false);
      toast({
        title: 'Success',
        description: 'World rule created successfully',
      });
    },
    onError: (error: any) => {
      console.error('Error creating world rule:', error);
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to create world rule. Please try again.',
        variant: 'destructive',
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: UpdateWorldRuleRequest }) =>
      updateWorldRule(ruleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['worldRules', trilogyId] });
      queryClient.invalidateQueries({ queryKey: ['worldRuleCategories', trilogyId] });
      setEditingRule(null);
      toast({
        title: 'Success',
        description: 'World rule updated successfully',
      });
    },
    onError: (error: any) => {
      console.error('Error updating world rule:', error);
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to update world rule. Please try again.',
        variant: 'destructive',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWorldRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['worldRules', trilogyId] });
      toast({
        title: 'Success',
        description: 'World rule deleted successfully',
      });
    },
    onError: (error: any) => {
      console.error('Error deleting world rule:', error);
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to delete world rule. Please try again.',
        variant: 'destructive',
      });
    },
  });

  // Handlers
  const handleCreate = async (data: CreateWorldRuleRequest) => {
    await createMutation.mutateAsync(data);
  };

  const handleUpdate = async (data: UpdateWorldRuleRequest) => {
    console.log('handleUpdate called with data:', data);
    if (editingRule) {
      console.log('Calling mutateAsync with ruleId:', editingRule.id);
      try {
        await updateMutation.mutateAsync({ ruleId: editingRule.id, data });
        console.log('mutateAsync completed successfully');
      } catch (error) {
        console.error('mutateAsync threw error:', error);
        throw error;
      }
    } else {
      console.error('No editingRule found!');
    }
  };

  const handleDelete = (ruleId: string) => {
    if (window.confirm('Are you sure you want to delete this rule? This action cannot be undone.')) {
      deleteMutation.mutate(ruleId);
    }
  };

  // Filter rules by search query
  const filteredRules = rulesData?.rules.filter((rule) =>
    searchQuery.trim() === '' ||
    rule.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    rule.description.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // Statistics
  const totalRules = rulesData?.total || 0;
  const lowAccuracyRules = filteredRules.filter(r => r.accuracy_rate < 0.6 && r.times_flagged > 5).length;

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      {/* Back Button */}
      <Button
        variant="ghost"
        onClick={() => navigate(`/trilogy/${trilogyId}`)}
        className="mb-6"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Trilogy
      </Button>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold">World Rules</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Define the foundational constraints and mechanics of your fictional universe
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/trilogy/${trilogyId}/rule-analytics`)}
              className="flex items-center gap-2"
            >
              <BarChart3 className="h-4 w-4" />
              View Analytics
            </Button>
            <Button onClick={() => setShowCreateDialog(true)} className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Create Rule
            </Button>
          </div>
        </div>

        {/* Statistics */}
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Total:</span>
            <span className="font-medium">{totalRules}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Categories:</span>
            <span className="font-medium">{categories.length}</span>
          </div>
          {lowAccuracyRules > 0 && (
            <div className="flex items-center gap-2 text-warning">
              <span>{lowAccuracyRules} need attention</span>
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search rules by title or description..."
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Category Filter */}
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-full md:w-[180px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Book Filter */}
        <Select value={selectedBookId} onValueChange={setSelectedBookId}>
          <SelectTrigger className="w-full md:w-[150px]">
            <BookOpen className="h-4 w-4 mr-2" />
            <SelectValue placeholder="All Books" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Books</SelectItem>
            {books.map((book) => (
              <SelectItem key={book.id} value={book.id}>
                Book {book.book_number}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* View Toggle */}
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

      {/* Error State */}
      {rulesError && (
        <Alert className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Error loading rules. Please try again.
          </AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {rulesLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      )}

      {/* Rules Display */}
      {!rulesLoading && (
        <>
          {filteredRules.length === 0 ? (
            <div className="text-center py-12 bg-muted rounded">
              <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-base font-medium text-foreground mb-2">No rules found</h3>
              <p className="text-muted-foreground text-sm mb-4">
                {searchQuery || (selectedCategory !== 'all') || (selectedBookId !== 'all')
                  ? 'Try adjusting your filters'
                  : 'Create your first world rule to get started'}
              </p>
              {!searchQuery && selectedCategory === 'all' && selectedBookId === 'all' && (
                <Button onClick={() => setShowCreateDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Rule
                </Button>
              )}
            </div>
          ) : viewMode === 'list' ? (
            /* List View */
            <div className="border rounded divide-y">
              {filteredRules.map((rule) => {
                const accuracyPercentage = Math.round(rule.accuracy_rate * 100);
                const getAccuracyColor = (rate: number): string => {
                  if (rate >= 0.8) return 'bg-success';
                  if (rate >= 0.6) return 'bg-warning';
                  return 'bg-destructive';
                };

                return (
                  <div
                    key={rule.id}
                    className="flex items-start gap-4 p-4 hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => setEditingRule(rule)}
                    onDoubleClick={() => setEditingRule(rule)}
                  >
                    <div className="w-10 h-10 rounded bg-accent/10 flex items-center justify-center flex-shrink-0">
                      <Globe className="w-5 h-5 text-accent" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-foreground">{rule.title}</h3>
                            <Badge variant="outline" className="text-xs">{rule.category}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                            {rule.description.length > 150
                              ? rule.description.slice(0, 150).trim() + '...'
                              : rule.description}
                          </p>
                          <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                            <span>{rule.book_ids.length} {rule.book_ids.length === 1 ? 'book' : 'books'}</span>
                            {rule.times_flagged > 0 && (
                              <span className="flex items-center gap-1">
                                <span className={`w-2 h-2 rounded-full ${getAccuracyColor(rule.accuracy_rate)}`} />
                                {accuracyPercentage}% accuracy
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingRule(rule)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(rule.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Card View */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredRules.map((rule) => (
                <WorldRuleCard
                  key={rule.id}
                  rule={rule}
                  onEdit={setEditingRule}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create World Rule</DialogTitle>
          </DialogHeader>
          <WorldRuleForm
            trilogyId={trilogyId}
            books={books}
            existingCategories={categories}
            onCreate={handleCreate}
            onSubmit={async () => {}}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingRule} onOpenChange={(open) => !open && setEditingRule(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit World Rule</DialogTitle>
          </DialogHeader>
          {editingRule && (
            <WorldRuleForm
              trilogyId={trilogyId}
              books={books}
              existingCategories={categories}
              rule={editingRule}
              onCreate={async () => {}}
              onSubmit={handleUpdate}
              onCancel={() => setEditingRule(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
