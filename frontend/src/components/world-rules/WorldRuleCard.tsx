/**
 * WorldRuleCard Component (Epic 3)
 *
 * Displays a single world rule with its details, accuracy metrics,
 * and action buttons.
 */

import React from 'react';
import type { WorldRule } from '@/api/worldRules';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Edit, Trash2 } from 'lucide-react';

interface WorldRuleCardProps {
  rule: WorldRule;
  onEdit?: (rule: WorldRule) => void;
  onDelete?: (ruleId: string) => void;
  showActions?: boolean;
}

export const WorldRuleCard: React.FC<WorldRuleCardProps> = ({
  rule,
  onEdit,
  onDelete,
  showActions = true,
}) => {
  // Calculate accuracy color
  const getAccuracyColor = (rate: number): string => {
    if (rate >= 0.8) return 'bg-success';
    if (rate >= 0.6) return 'bg-warning';
    return 'bg-destructive';
  };

  // Format accuracy percentage
  const accuracyPercentage = Math.round(rule.accuracy_rate * 100);

  return (
    <Card
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onEdit?.(rule)}
      onDoubleClick={() => onEdit?.(rule)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold">{rule.title}</CardTitle>
            <CardDescription className="mt-1">
              <Badge variant="outline" className="mr-2">
                {rule.category}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {rule.book_ids.length} {rule.book_ids.length === 1 ? 'book' : 'books'}
              </span>
            </CardDescription>
          </div>

          {/* Accuracy Badge */}
          {rule.times_flagged > 0 && (
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${getAccuracyColor(rule.accuracy_rate)}`} />
              <span className="text-sm font-medium">{accuracyPercentage}%</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3">{rule.description}</p>

        {/* Consistency Metrics */}
        {rule.times_flagged > 0 && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs font-medium text-muted-foreground mb-2">Consistency Metrics</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Flagged:</span>
                <span className="ml-2 font-medium">{rule.times_flagged}</span>
              </div>
              <div>
                <span className="text-muted-foreground">True Violations:</span>
                <span className="ml-2 font-medium">{rule.times_true_violation}</span>
              </div>
              <div>
                <span className="text-muted-foreground">False Positives:</span>
                <span className="ml-2 font-medium">{rule.times_false_positive}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Intentional Breaks:</span>
                <span className="ml-2 font-medium">{rule.times_intentional_break}</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>

      {showActions && (
        <CardFooter className="flex gap-1 justify-end pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit?.(rule)}
          >
            <Edit className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete?.(rule.id)}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </CardFooter>
      )}
    </Card>
  );
};

/**
 * Compact version for sidebars or lists
 */
export const WorldRuleCompactCard: React.FC<{
  rule: WorldRule;
  onClick?: () => void;
}> = ({ rule, onClick }) => {
  return (
    <div
      className="p-3 border border-border rounded-lg hover:bg-muted cursor-pointer transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="text-sm font-medium">{rule.title}</h4>
          <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{rule.description}</p>
        </div>
        <Badge variant="outline" className="ml-2 text-xs">
          {rule.category}
        </Badge>
      </div>
      {rule.accuracy_rate < 0.6 && rule.times_flagged > 5 && (
        <div className="mt-2">
          <Badge variant="destructive" className="text-xs">
            Low Accuracy ({Math.round(rule.accuracy_rate * 100)}%)
          </Badge>
        </div>
      )}
    </div>
  );
};
