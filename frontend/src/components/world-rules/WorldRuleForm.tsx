/**
 * WorldRuleForm Component (Epic 3)
 *
 * Form for creating and editing world rules.
 * Supports multi-book selection and category management.
 */

import React, { useState } from 'react';
import type { WorldRule, CreateWorldRuleRequest, UpdateWorldRuleRequest } from '@/api/worldRules';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { X } from 'lucide-react';

interface WorldRuleFormProps {
  trilogyId: string;
  books: Array<{ id: string; title: string; book_number: number }>;
  existingCategories: string[];
  rule?: WorldRule; // If provided, form is in edit mode
  onSubmit: (data: UpdateWorldRuleRequest) => Promise<void>;
  onCreate: (data: CreateWorldRuleRequest) => Promise<void>;
  onCancel: () => void;
}

export const WorldRuleForm: React.FC<WorldRuleFormProps> = ({
  trilogyId,
  books,
  existingCategories,
  rule,
  onSubmit,
  onCreate,
  onCancel,
}) => {
  const [title, setTitle] = useState(rule?.title || '');
  const [description, setDescription] = useState(rule?.description || '');
  const [category, setCategory] = useState(rule?.category || '');
  const [selectedBookIds, setSelectedBookIds] = useState<string[]>(rule?.book_ids || []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCategoryInput, setShowCategoryInput] = useState(false);

  const isEditMode = !!rule;

  // Handle book selection toggle
  const toggleBookSelection = (bookId: string) => {
    setSelectedBookIds((prev) =>
      prev.includes(bookId) ? prev.filter((id) => id !== bookId) : [...prev, bookId]
    );
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Safety timeout - prevent infinite hanging
    const timeoutId = setTimeout(() => {
      console.error('Form submission timed out after 30 seconds');
      setIsSubmitting(false);
      alert('Save operation timed out. Please try again.');
    }, 30000);

    try {
      if (isEditMode) {
        // Update mode - only send changed fields
        const updates: UpdateWorldRuleRequest = {};
        if (title !== rule.title) updates.title = title;
        if (description !== rule.description) updates.description = description;
        if (category !== rule.category) updates.category = category;
        if (JSON.stringify(selectedBookIds) !== JSON.stringify(rule.book_ids)) {
          updates.book_ids = selectedBookIds;
        }
        await onSubmit(updates);
      } else {
        // Create mode
        const data: CreateWorldRuleRequest = {
          trilogy_id: trilogyId,
          title,
          description,
          category,
          book_ids: selectedBookIds,
        };
        await onCreate(data);
      }
      clearTimeout(timeoutId);
    } catch (error) {
      clearTimeout(timeoutId);
      console.error('Error submitting world rule:', error);
      // Error will be handled by the mutation's onError callback in parent component
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Check if form is valid
  const isValid =
    title.trim().length > 0 &&
    description.trim().length > 0 &&
    category.trim().length > 0 &&
    selectedBookIds.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEditMode ? 'Edit World Rule' : 'Create New World Rule'}</CardTitle>
        <CardDescription>
          {isEditMode
            ? 'Update the rule details and book associations'
            : 'Define a foundational constraint or mechanic of your fictional universe'}
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-6">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Rule Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTitle(e.target.value)}
              placeholder="e.g., Speed of Light Constant"
              maxLength={200}
              required
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description *</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed explanation of this world rule..."
              rows={4}
              maxLength={5000}
              required
            />
            <p className="text-xs text-muted-foreground">{description.length} / 5000 characters</p>
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label htmlFor="category">Category *</Label>
            {!showCategoryInput && existingCategories.length > 0 ? (
              <div className="space-y-2">
                <select
                  id="category"
                  value={category}
                  onChange={(e) => {
                    if (e.target.value === '__new__') {
                      setShowCategoryInput(true);
                      setCategory('');
                    } else {
                      setCategory(e.target.value);
                    }
                  }}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-ring bg-background text-foreground"
                  required
                >
                  <option value="">Select a category...</option>
                  {existingCategories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                  <option value="__new__">+ Create new category</option>
                </select>
              </div>
            ) : (
              <div className="flex gap-2">
                <Input
                  id="category"
                  value={category}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCategory(e.target.value)}
                  placeholder="e.g., physics, consciousness, technology"
                  maxLength={100}
                  required
                />
                {existingCategories.length > 0 && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowCategoryInput(false);
                      setCategory('');
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Book Selection */}
          <div className="space-y-3">
            <Label>Applies to Books *</Label>
            <p className="text-sm text-muted-foreground">
              Select which books this rule applies to. Rules can evolve across your trilogy.
            </p>
            <div className="space-y-2">
              {books.map((book) => (
                <div key={book.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`book-${book.id}`}
                    checked={selectedBookIds.includes(book.id)}
                    onCheckedChange={() => toggleBookSelection(book.id)}
                  />
                  <label
                    htmlFor={`book-${book.id}`}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    Book {book.book_number}: {book.title}
                  </label>
                </div>
              ))}
            </div>
            {selectedBookIds.length === 0 && (
              <p className="text-xs text-red-500">Please select at least one book</p>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex justify-end gap-3 border-t pt-6">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" disabled={!isValid || isSubmitting}>
            {isSubmitting ? 'Saving...' : isEditMode ? 'Update Rule' : 'Create Rule'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
