/**
 * Rule Preview Dialog Component (Epic 5B)
 *
 * Shows which world rules will be included in content generation
 * before the user triggers generation. Allows them to see relevance
 * and similarity scores.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertCircle, CheckCircle, Sparkles } from 'lucide-react';
import { previewRulesForGeneration, type RulePreviewRequest, type RulePreviewResponse } from '@/api/worldRules';

interface RulePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  previewParams: RulePreviewRequest | null;
  onConfirm: () => void;
}

export function RulePreviewDialog({
  open,
  onOpenChange,
  previewParams,
  onConfirm,
}: RulePreviewDialogProps) {
  const [showPrompt, setShowPrompt] = useState(false);

  // Fetch rule preview
  // Disable TanStack Query caching - always fetch fresh data from backend
  // Backend Redis cache is invalidated when rules are created/updated
  const { data, isLoading, error } = useQuery<RulePreviewResponse>({
    queryKey: ['rulePreview', previewParams],
    queryFn: () => previewRulesForGeneration(previewParams!),
    enabled: open && previewParams !== null,
    staleTime: 0, // Always consider data stale
    gcTime: 0, // Don't cache results (renamed from cacheTime in v5)
    refetchOnMount: 'always', // Always refetch when dialog opens
  });

  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            World Rules Preview
          </DialogTitle>
          <DialogDescription>
            These rules will be included in the generation prompt to ensure consistency
            with your universe's mechanics and lore.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 pr-4 max-h-[50vh]">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Loading relevant rules...</span>
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load rule preview. You can still proceed with generation.
              </AlertDescription>
            </Alert>
          )}

          {data && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm font-medium">
                    {data.rules.length} rules will be included
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {data.cache_hit ? 'Retrieved from cache' : 'Freshly retrieved'}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowPrompt(!showPrompt)}
                >
                  {showPrompt ? 'Hide' : 'Show'} Formatted Prompt
                </Button>
              </div>

              {/* Formatted Prompt Section */}
              {showPrompt && (
                <div className="p-4 bg-slate-950 rounded-lg">
                  <pre className="text-xs text-slate-200 whitespace-pre-wrap font-mono">
                    {data.formatted_prompt_section}
                  </pre>
                </div>
              )}

              {/* Rules List */}
              {data.rules.length === 0 ? (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No relevant rules found for this scene. Generation will proceed with
                    character context only.
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="space-y-3">
                  {data.rules.map((rule, index) => (
                    <div
                      key={rule.id}
                      className="p-4 border rounded-lg space-y-2 hover:bg-muted/50 transition-colors"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-muted-foreground">
                              #{index + 1}
                            </span>
                            <h4 className="font-medium">{rule.title}</h4>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {rule.relevance_reason}
                          </p>
                        </div>

                        {/* Badges */}
                        <div className="flex flex-col items-end gap-1">
                          <Badge variant="secondary" className="text-xs">
                            {rule.category}
                          </Badge>
                          <div className="flex items-center gap-1">
                            <Badge
                              variant={rule.is_critical ? 'default' : 'outline'}
                              className="text-xs"
                            >
                              {(rule.similarity * 100).toFixed(0)}% match
                            </Badge>
                            {rule.is_critical && (
                              <CheckCircle className="h-3 w-3 text-green-500" />
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-sm text-muted-foreground pl-6">
                        {rule.description}
                      </p>

                      {/* Accuracy Info */}
                      {rule.accuracy_rate !== undefined && rule.accuracy_rate < 1 && (
                        <div className="pl-6">
                          <Badge variant="outline" className="text-xs">
                            {(rule.accuracy_rate * 100).toFixed(0)}% accuracy
                          </Badge>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Generate with {data?.rules.length || 0} Rules
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
