-- Migration: Add is_current flag to sub_chapter_versions table
-- This flag tracks which version is currently active for each sub-chapter
-- Only one version per sub-chapter should have is_current = true

-- Add the is_current column
ALTER TABLE sub_chapter_versions
ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT false;

-- Create an index for faster lookups of current versions
CREATE INDEX IF NOT EXISTS idx_sub_chapter_versions_is_current
ON sub_chapter_versions(sub_chapter_id, is_current)
WHERE is_current = true;

-- Backfill: Set is_current = true for the latest version of each sub-chapter
WITH latest_versions AS (
    SELECT DISTINCT ON (sub_chapter_id) id
    FROM sub_chapter_versions
    ORDER BY sub_chapter_id, version_number DESC
)
UPDATE sub_chapter_versions
SET is_current = true
WHERE id IN (SELECT id FROM latest_versions);

-- Add comment for documentation
COMMENT ON COLUMN sub_chapter_versions.is_current IS 'Indicates if this is the currently active version for the sub-chapter. Only one version per sub-chapter should be true.';
