-- Migration: Add primary trilogy feature
-- Date: 2025-01-21
-- Description: Adds is_primary column to trilogy_projects table with unique constraint

-- Add is_primary column (default false)
ALTER TABLE trilogy_projects
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

-- Create partial unique index to ensure only ONE primary trilogy per user
-- This prevents multiple trilogies from being primary for the same user
DROP INDEX IF EXISTS idx_one_primary_per_user;
CREATE UNIQUE INDEX idx_one_primary_per_user
ON trilogy_projects (user_id)
WHERE is_primary = TRUE;

-- Optional: Set the most recently updated trilogy as primary for existing users
-- This ensures backward compatibility for users who already have trilogies
UPDATE trilogy_projects t1
SET is_primary = TRUE
WHERE t1.id = (
  SELECT t2.id
  FROM trilogy_projects t2
  WHERE t2.user_id = t1.user_id
  ORDER BY t2.updated_at DESC
  LIMIT 1
)
AND NOT EXISTS (
  SELECT 1
  FROM trilogy_projects t3
  WHERE t3.user_id = t1.user_id
  AND t3.is_primary = TRUE
);
