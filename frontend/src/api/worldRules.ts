/**
 * World Rules API Client (Epic 3)
 *
 * Handles all world rule operations including CRUD, contextual search,
 * and RAG integration.
 */

import { apiClient } from './client';

// ============================================================================
// Types
// ============================================================================

export interface WorldRule {
  id: string;
  trilogy_id: string;
  title: string;
  description: string;
  category: string;
  created_at: string;
  updated_at: string;
  times_flagged: number;
  times_true_violation: number;
  times_false_positive: number;
  times_intentional_break: number;
  times_checker_error: number;
  accuracy_rate: number;
  book_ids: string[];
}

export interface CreateWorldRuleRequest {
  trilogy_id: string;
  title: string;
  description: string;
  category: string;
  book_ids: string[];
}

export interface UpdateWorldRuleRequest {
  title?: string;
  description?: string;
  category?: string;
  book_ids?: string[];
}

export interface WorldRuleListResponse {
  rules: WorldRule[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface WorldRuleContext {
  id: string;
  title: string;
  description: string;
  category: string;
  similarity: number;
  relevance_reason: string;
  is_critical: boolean;
  accuracy_rate: number;
}

export interface RulePreviewRequest {
  prompt: string;
  plot_points: string;
  book_id: string;
  trilogy_id: string;
  max_rules?: number;
  similarity_threshold?: number;
}

export interface RulePreviewResponse {
  rules: WorldRuleContext[];
  formatted_prompt_section: string;
  cache_hit: boolean;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Create a new world rule
 */
export const createWorldRule = async (data: CreateWorldRuleRequest): Promise<WorldRule> => {
  const response = await apiClient.post('/api/world_rules', data);
  return response.data;
};

/**
 * List world rules for a trilogy with optional filters
 */
export const listWorldRules = async (params: {
  trilogy_id: string;
  category?: string;
  book_id?: string;
  page?: number;
  page_size?: number;
}): Promise<WorldRuleListResponse> => {
  const response = await apiClient.get('/api/world_rules', { params });
  return response.data;
};

/**
 * Get a single world rule by ID
 */
export const getWorldRule = async (ruleId: string): Promise<WorldRule> => {
  const response = await apiClient.get(`/api/world_rules/${ruleId}`);
  return response.data;
};

/**
 * Update an existing world rule
 */
export const updateWorldRule = async (
  ruleId: string,
  data: UpdateWorldRuleRequest
): Promise<WorldRule> => {
  console.log('updateWorldRule called with ruleId:', ruleId, 'data:', data);
  console.log('About to call apiClient.put...');
  const response = await apiClient.put(`/api/world_rules/${ruleId}`, data);
  console.log('apiClient.put completed, response:', response);
  return response.data;
};

/**
 * Delete a world rule
 */
export const deleteWorldRule = async (ruleId: string): Promise<void> => {
  await apiClient.delete(`/api/world_rules/${ruleId}`);
};

/**
 * Get unique categories for a trilogy
 */
export const getCategories = async (trilogyId: string): Promise<string[]> => {
  const response = await apiClient.get('/api/world_rules/categories/list', {
    params: { trilogy_id: trilogyId },
  });
  return response.data.categories;
};

/**
 * Get contextually relevant rules for a writing prompt
 */
export const getContextualRules = async (params: {
  prompt: string;
  book_id: string;
  trilogy_id: string;
  similarity_threshold?: number;
  max_rules?: number;
}): Promise<WorldRuleContext[]> => {
  const response = await apiClient.get('/api/world_rules/contextual/search', { params });
  return response.data.rules;
};

/**
 * Preview rules that would be used for content generation
 */
export const previewRulesForGeneration = async (
  data: RulePreviewRequest
): Promise<RulePreviewResponse> => {
  const response = await apiClient.post('/api/world_rules/preview', data);
  return response.data;
};

/**
 * Get rules by category for a specific book
 */
export const getRulesByCategory = async (params: {
  category: string;
  trilogy_id: string;
  book_id: string;
  max_rules?: number;
}): Promise<WorldRuleContext[]> => {
  const { category, ...queryParams } = params;
  const response = await apiClient.get(`/api/world_rules/category/${category}`, {
    params: queryParams,
  });
  return response.data.rules;
};

/**
 * Get high-accuracy "golden rules" for a book
 */
export const getCriticalRules = async (params: {
  trilogy_id: string;
  book_id: string;
  min_accuracy?: number;
}): Promise<WorldRuleContext[]> => {
  const response = await apiClient.get('/api/world_rules/critical/list', { params });
  return response.data.rules;
};

/**
 * Trigger batch embedding for all rules in a trilogy
 */
export const batchEmbedTrilogy = async (trilogyId: string): Promise<{ job_id: string }> => {
  const response = await apiClient.post('/api/world_rules/batch/embed-trilogy', null, {
    params: { trilogy_id: trilogyId },
  });
  return response.data;
};

// ============================================================================
// Analytics & Metrics (Epic 5B)
// ============================================================================

export interface RuleUsageAnalytics {
  rule_id: string;
  title: string;
  category: string;
  times_flagged: number;
  times_true_violation: number;
  times_false_positive: number;
  times_intentional_break: number;
  times_checker_error: number;
  accuracy_rate: number;
}

export interface RuleUsageAnalyticsResponse {
  trilogy_id: string;
  filters: {
    book_id?: string;
    category?: string;
  };
  summary: {
    total_rules: number;
    total_times_flagged: number;
    total_violations: number;
    total_intentional_breaks: number;
    average_accuracy_rate: number;
  };
  most_used_rules: RuleUsageAnalytics[];
  all_rules: RuleUsageAnalytics[];
}

export interface CategoryEffectiveness {
  category: string;
  trilogy_id: string;
  total_rules: number;
  rules_used: number;
  avg_category_accuracy: number;
  total_flags: number;
  total_violations: number;
  total_intentional_breaks: number;
}

export interface CategoryEffectivenessResponse {
  trilogy_id: string;
  category_effectiveness: CategoryEffectiveness[];
}

export interface SubChapterRuleUsage {
  rule_id: string;
  rule_title: string;
  rule_category: string;
  similarity: number;
  was_followed: boolean;
  was_violated: boolean;
}

export interface SubChapterRuleUsageResponse {
  sub_chapter_id: string;
  rules_used: SubChapterRuleUsage[];
}

/**
 * Get rule usage analytics for a trilogy (Epic 5B)
 */
export const getRuleUsageAnalytics = async (params: {
  trilogy_id: string;
  book_id?: string;
  category?: string;
  limit?: number;
}): Promise<RuleUsageAnalyticsResponse> => {
  const response = await apiClient.get('/api/world_rules/analytics/usage', { params });
  return response.data;
};

/**
 * Get rule effectiveness by category (Epic 5B)
 */
export const getRuleEffectivenessByCategory = async (
  trilogyId: string
): Promise<CategoryEffectivenessResponse> => {
  const response = await apiClient.get('/api/world_rules/analytics/effectiveness', {
    params: { trilogy_id: trilogyId },
  });
  return response.data;
};

/**
 * Get rules used during specific sub-chapter generation (Epic 5B)
 */
export const getSubChapterRuleUsage = async (
  subChapterId: string
): Promise<SubChapterRuleUsageResponse> => {
  const response = await apiClient.get(`/api/world_rules/analytics/sub-chapter/${subChapterId}`);
  return response.data;
};
