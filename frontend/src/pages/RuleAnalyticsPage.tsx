/**
 * Rule Analytics Page (Epic 5B)
 *
 * Dashboard showing world rule usage analytics and effectiveness metrics.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getRuleUsageAnalytics,
  getRuleEffectivenessByCategory,
  getCategories,
} from '@/api/worldRules';
import { getTrilogy } from '@/api/trilogy';
import { ArrowLeft, BarChart3, TrendingUp, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function RuleAnalyticsPage() {
  const { trilogyId } = useParams<{ trilogyId: string }>();
  const navigate = useNavigate();

  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);

  // Fetch trilogy details
  const { data: trilogy } = useQuery({
    queryKey: ['trilogy', trilogyId],
    queryFn: () => getTrilogy(trilogyId!),
    enabled: !!trilogyId,
  });

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories', trilogyId],
    queryFn: () => getCategories(trilogyId!),
    enabled: !!trilogyId,
  });

  // Fetch usage analytics
  const {
    data: usageData,
    isLoading: usageLoading,
    error: usageError,
  } = useQuery({
    queryKey: ['ruleUsageAnalytics', trilogyId, selectedCategory],
    queryFn: () =>
      getRuleUsageAnalytics({
        trilogy_id: trilogyId!,
        category: selectedCategory,
        limit: 50,
      }),
    enabled: !!trilogyId,
  });

  // Fetch effectiveness data
  const {
    data: effectivenessData,
    isLoading: effectivenessLoading,
  } = useQuery({
    queryKey: ['ruleEffectiveness', trilogyId],
    queryFn: () => getRuleEffectivenessByCategory(trilogyId!),
    enabled: !!trilogyId,
  });

  if (!trilogyId) {
    return <div>Trilogy not found</div>;
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(`/trilogy/${trilogyId}/world-rules`)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-foreground text-3xl font-bold">Rule Analytics</h1>
            <p className="text-muted-foreground">
              {trilogy?.title || 'Loading...'} - Usage & Effectiveness Metrics
            </p>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {usageData && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Rules</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{usageData.summary.total_rules}</div>
              <p className="text-xs text-muted-foreground">
                Across all categories
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Flags</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {usageData.summary.total_times_flagged?.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-muted-foreground">
                Times rules were checked
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Accuracy</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {((usageData.summary.average_accuracy_rate || 0) * 100).toFixed(1)}%
              </div>
              <p className="text-xs text-muted-foreground">
                Average rule accuracy
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Category Filter */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium">Filter by Category:</label>
        <Select
          value={selectedCategory || 'all'}
          onValueChange={(value) => setSelectedCategory(value === 'all' ? undefined : value)}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((category) => (
              <SelectItem key={category} value={category}>
                {category}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Category Effectiveness */}
      <Card>
        <CardHeader>
          <CardTitle>Effectiveness by Category</CardTitle>
          <CardDescription>
            Which categories of rules are most effective at preventing violations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {effectivenessLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : effectivenessData && effectivenessData.category_effectiveness.length > 0 ? (
            <div className="space-y-4">
              {effectivenessData.category_effectiveness.map((cat) => (
                <div key={cat.category} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{cat.category}</span>
                      <Badge variant="secondary" className="text-xs">
                        {cat.rules_used}/{cat.total_rules} used
                      </Badge>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {cat.avg_category_accuracy !== null && cat.avg_category_accuracy !== undefined
                        ? `${(cat.avg_category_accuracy * 100).toFixed(1)}% accuracy`
                        : 'No data'}
                    </span>
                  </div>
                  {cat.avg_category_accuracy !== null && cat.avg_category_accuracy !== undefined && (
                    <Progress value={cat.avg_category_accuracy * 100} className="h-2" />
                  )}
                  <p className="text-xs text-muted-foreground">
                    {cat.total_flags?.toLocaleString() || 0} total flags · {cat.total_violations || 0} violations
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <Alert>
              <AlertDescription>
                No category effectiveness data available yet. Generate some content to see analytics.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Most Used Rules */}
      <Card>
        <CardHeader>
          <CardTitle>Most Used Rules</CardTitle>
          <CardDescription>
            Rules that appear most frequently in content generation
          </CardDescription>
        </CardHeader>
        <CardContent>
          {usageLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : usageError ? (
            <Alert variant="destructive">
              <AlertDescription>
                Failed to load usage analytics. Please try again.
              </AlertDescription>
            </Alert>
          ) : usageData && usageData.most_used_rules.length > 0 ? (
            <div className="space-y-3">
              {usageData.most_used_rules.map((rule, index) => (
                <div
                  key={rule.id}
                  className="p-4 border rounded-lg space-y-2 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-muted-foreground">
                          #{index + 1}
                        </span>
                        <h4 className="font-medium">{rule.title}</h4>
                      </div>
                    </div>
                    <Badge variant="secondary">{rule.category}</Badge>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-muted-foreground pl-6">
                    <span key="flagged" className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      Flagged {rule.times_flagged || 0}x
                    </span>
                    {rule.accuracy_rate !== null && rule.accuracy_rate !== undefined && (
                      <span key="accuracy" className="flex items-center gap-1">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        {(rule.accuracy_rate * 100).toFixed(1)}% accuracy
                      </span>
                    )}
                    {(rule.times_true_violation || 0) > 0 && (
                      <span key="violations" className="flex items-center gap-1">
                        <XCircle className="h-3 w-3 text-destructive" />
                        {rule.times_true_violation} violations
                      </span>
                    )}
                    {(rule.times_intentional_break || 0) > 0 && (
                      <span key="intentional" className="flex items-center gap-1">
                        <CheckCircle className="h-3 w-3 text-accent" />
                        {rule.times_intentional_break} intentional breaks
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Alert>
              <AlertDescription>
                No usage data available yet. Generate some content with world rules to see analytics.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
