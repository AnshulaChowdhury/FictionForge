-- Epic 5B: Sub-Chapter Generation Metadata Table
-- Tracks which world rules were used during content generation for analytics and learning

-- ============================================================================
-- Main Table: sub_chapter_generation_metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS sub_chapter_generation_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sub_chapter_id UUID NOT NULL REFERENCES sub_chapters(id) ON DELETE CASCADE,
    generation_timestamp TIMESTAMP DEFAULT NOW(),

    -- Context used
    world_rule_ids UUID[],  -- Array of rule IDs used in generation
    world_rule_similarities JSONB,  -- Map of rule_id -> similarity score
    character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
    character_context_chunks INTEGER DEFAULT 0,  -- Number of character context chunks used

    -- Generation details
    model_used VARCHAR(100),
    prompt_token_count INTEGER,
    generation_token_count INTEGER,

    -- Post-generation analysis (populated by consistency checker)
    rules_followed_count INTEGER,
    rules_violated_count INTEGER,
    violated_rule_ids UUID[],  -- Rules that were violated despite being in prompt

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_gen_metadata_subchapter
    ON sub_chapter_generation_metadata(sub_chapter_id);

CREATE INDEX IF NOT EXISTS idx_gen_metadata_timestamp
    ON sub_chapter_generation_metadata(generation_timestamp);

CREATE INDEX IF NOT EXISTS idx_gen_metadata_character
    ON sub_chapter_generation_metadata(character_id);

-- GIN index for array searches (which rules were used)
CREATE INDEX IF NOT EXISTS idx_gen_metadata_rule_ids
    ON sub_chapter_generation_metadata USING GIN(world_rule_ids);

-- ============================================================================
-- Analytics View: World Rule Usage Analytics
-- ============================================================================

CREATE OR REPLACE VIEW world_rule_usage_analytics AS
SELECT
    wr.id,
    wr.title,
    wr.category,
    wr.trilogy_id,
    COUNT(DISTINCT sgm.sub_chapter_id) as times_used_in_generation,
    AVG(
        CASE
            WHEN sgm.rules_followed_count + sgm.rules_violated_count > 0
            THEN sgm.rules_followed_count::FLOAT /
                 (sgm.rules_followed_count + sgm.rules_violated_count)
            ELSE NULL
        END
    ) as avg_adherence_rate,
    COUNT(DISTINCT CASE WHEN wr.id = ANY(sgm.violated_rule_ids) THEN sgm.id END) as times_violated_in_prompt,
    COUNT(DISTINCT CASE WHEN wr.id = ANY(sgm.world_rule_ids)
                         AND NOT (wr.id = ANY(sgm.violated_rule_ids))
                        THEN sgm.id END) as times_followed_in_prompt
FROM world_rules wr
LEFT JOIN sub_chapter_generation_metadata sgm
    ON wr.id = ANY(sgm.world_rule_ids)
GROUP BY wr.id, wr.title, wr.category, wr.trilogy_id;

-- ============================================================================
-- Analytics View: Rule Effectiveness by Category
-- ============================================================================

CREATE OR REPLACE VIEW rule_category_effectiveness AS
SELECT
    wr.category,
    wr.trilogy_id,
    COUNT(DISTINCT wr.id) as total_rules,
    COUNT(DISTINCT CASE WHEN sgm.id IS NOT NULL THEN wr.id END) as rules_used,
    AVG(
        CASE
            WHEN sgm.rules_followed_count + sgm.rules_violated_count > 0
            THEN sgm.rules_followed_count::FLOAT /
                 (sgm.rules_followed_count + sgm.rules_violated_count)
            ELSE NULL
        END
    ) as avg_category_adherence,
    COUNT(DISTINCT sgm.sub_chapter_id) as total_generations_with_category
FROM world_rules wr
LEFT JOIN sub_chapter_generation_metadata sgm
    ON wr.id = ANY(sgm.world_rule_ids)
GROUP BY wr.category, wr.trilogy_id;

-- ============================================================================
-- Function: Get Rule Usage for a Generation
-- ============================================================================

CREATE OR REPLACE FUNCTION get_generation_rule_usage(p_sub_chapter_id UUID)
RETURNS TABLE (
    rule_id UUID,
    rule_title VARCHAR,
    rule_category VARCHAR,
    similarity FLOAT,
    was_followed BOOLEAN,
    was_violated BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wr.id,
        wr.title,
        wr.category,
        (sgm.world_rule_similarities->wr.id::text)::FLOAT as similarity,
        NOT (wr.id = ANY(sgm.violated_rule_ids)) as was_followed,
        (wr.id = ANY(sgm.violated_rule_ids)) as was_violated
    FROM sub_chapter_generation_metadata sgm
    CROSS JOIN unnest(sgm.world_rule_ids) as rule_id_unnest
    JOIN world_rules wr ON wr.id = rule_id_unnest
    WHERE sgm.sub_chapter_id = p_sub_chapter_id
    ORDER BY (sgm.world_rule_similarities->wr.id::text)::FLOAT DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE sub_chapter_generation_metadata IS
'Tracks which world rules were used during content generation for analytics and learning. Part of Epic 5B.';

COMMENT ON COLUMN sub_chapter_generation_metadata.world_rule_ids IS
'Array of world rule UUIDs that were included in the generation prompt';

COMMENT ON COLUMN sub_chapter_generation_metadata.world_rule_similarities IS
'JSONB map of rule_id to similarity score (0-1) for analytics';

COMMENT ON COLUMN sub_chapter_generation_metadata.violated_rule_ids IS
'Rules that were violated despite being included in the generation prompt. Indicates ineffective rules.';

COMMENT ON VIEW world_rule_usage_analytics IS
'Analytics view showing how often each rule is used and its effectiveness (adherence rate)';

COMMENT ON VIEW rule_category_effectiveness IS
'Analytics view showing effectiveness metrics aggregated by rule category';
