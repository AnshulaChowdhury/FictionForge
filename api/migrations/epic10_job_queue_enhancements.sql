-- ============================================================================
-- EPIC 10: ASYNC JOB QUEUE SYSTEM - Database Enhancements
-- ============================================================================
-- This migration updates the existing generation_jobs table and adds
-- user_notification_preferences and character vector store tracking

-- ============================================================================
-- PART 1: Update generation_jobs Table
-- ============================================================================

-- Add new columns for Epic 10 progress tracking
ALTER TABLE generation_jobs
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS arq_job_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS stage VARCHAR(255),
ADD COLUMN IF NOT EXISTS progress_percentage INTEGER DEFAULT 0
    CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
ADD COLUMN IF NOT EXISTS estimated_completion TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS word_count INTEGER,
ADD COLUMN IF NOT EXISTS version_id UUID REFERENCES sub_chapter_versions(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS version_number INTEGER,
ADD COLUMN IF NOT EXISTS generation_params JSONB;

-- Backfill user_id from created_by_user_id if not set
UPDATE generation_jobs
SET user_id = created_by_user_id
WHERE user_id IS NULL AND created_by_user_id IS NOT NULL;

-- Make user_id NOT NULL after backfill
ALTER TABLE generation_jobs
ALTER COLUMN user_id SET NOT NULL;

-- Drop old status constraint and add new one with additional statuses
ALTER TABLE generation_jobs DROP CONSTRAINT IF EXISTS generation_jobs_status_check;
ALTER TABLE generation_jobs
ADD CONSTRAINT generation_jobs_status_check
CHECK (status IN ('queued', 'pending', 'in_progress', 'completed', 'failed', 'cancelled'));

-- Update existing 'pending' status to 'queued' for consistency
UPDATE generation_jobs SET status = 'queued' WHERE status = 'pending';

-- Update existing 'processing' status to 'in_progress' for consistency
UPDATE generation_jobs SET status = 'in_progress' WHERE status = 'processing';

-- ============================================================================
-- PART 2: Add Indexes for Epic 10
-- ============================================================================

-- Index for querying user's active jobs
CREATE INDEX IF NOT EXISTS idx_generation_jobs_user_status
ON generation_jobs(user_id, status)
WHERE status IN ('queued', 'in_progress');

-- Index for querying by Arq job ID
CREATE INDEX IF NOT EXISTS idx_generation_jobs_arq_job_id
ON generation_jobs(arq_job_id);

-- Index for cleanup of old jobs
CREATE INDEX IF NOT EXISTS idx_generation_jobs_completed_at
ON generation_jobs(completed_at)
WHERE completed_at IS NOT NULL;

-- ============================================================================
-- PART 3: Add Triggers for Automatic Timestamps
-- ============================================================================

-- Trigger: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_generation_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS generation_jobs_updated_at_trigger ON generation_jobs;
CREATE TRIGGER generation_jobs_updated_at_trigger
BEFORE UPDATE ON generation_jobs
FOR EACH ROW
EXECUTE FUNCTION update_generation_jobs_updated_at();

-- Trigger: Set started_at when status changes to 'in_progress'
CREATE OR REPLACE FUNCTION set_generation_job_started_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'in_progress'
       AND (OLD.status IS NULL OR OLD.status != 'in_progress')
       AND NEW.started_at IS NULL THEN
        NEW.started_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS generation_jobs_started_at_trigger ON generation_jobs;
CREATE TRIGGER generation_jobs_started_at_trigger
BEFORE UPDATE ON generation_jobs
FOR EACH ROW
EXECUTE FUNCTION set_generation_job_started_at();

-- Trigger: Set completed_at when status changes to terminal state
CREATE OR REPLACE FUNCTION set_generation_job_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('completed', 'failed', 'cancelled')
       AND (OLD.status IS NULL OR OLD.status NOT IN ('completed', 'failed', 'cancelled'))
       AND NEW.completed_at IS NULL THEN
        NEW.completed_at = NOW();
        NEW.progress_percentage = 100;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS generation_jobs_completed_at_trigger ON generation_jobs;
CREATE TRIGGER generation_jobs_completed_at_trigger
BEFORE UPDATE ON generation_jobs
FOR EACH ROW
EXECUTE FUNCTION set_generation_job_completed_at();

-- ============================================================================
-- PART 4: Enable RLS on generation_jobs
-- ============================================================================

ALTER TABLE generation_jobs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS generation_jobs_user_isolation ON generation_jobs;

-- Policy: Users can only see their own jobs
CREATE POLICY generation_jobs_user_isolation
ON generation_jobs
FOR ALL
USING (auth.uid() = user_id);

-- ============================================================================
-- PART 5: Create user_notification_preferences Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email_notifications_enabled BOOLEAN DEFAULT TRUE,
    toast_notifications_enabled BOOLEAN DEFAULT TRUE,
    notification_email VARCHAR,
    notify_on_success BOOLEAN DEFAULT TRUE,
    notify_on_failure BOOLEAN DEFAULT TRUE,
    notify_on_long_tasks BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_notification_preferences ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own notification preferences"
ON user_notification_preferences FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notification preferences"
ON user_notification_preferences FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notification preferences"
ON user_notification_preferences FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_notification_prefs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notification_prefs_updated_at_trigger
BEFORE UPDATE ON user_notification_preferences
FOR EACH ROW
EXECUTE FUNCTION update_notification_prefs_updated_at();

-- ============================================================================
-- PART 6: Update characters Table for Vector Store Status
-- ============================================================================

-- Add vector store status tracking columns
ALTER TABLE characters
ADD COLUMN IF NOT EXISTS vector_store_collection VARCHAR,
ADD COLUMN IF NOT EXISTS vector_store_initialized_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS vector_store_initialization_failed_at TIMESTAMP;

-- Index for vector store collection lookup
CREATE INDEX IF NOT EXISTS idx_characters_vector_collection
ON characters(vector_store_collection)
WHERE vector_store_collection IS NOT NULL;

-- ============================================================================
-- PART 7: Helper Functions
-- ============================================================================

-- Function: Get active jobs with enriched data
CREATE OR REPLACE FUNCTION get_active_generation_jobs(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    trilogy_id UUID,
    sub_chapter_id UUID,
    sub_chapter_title VARCHAR,
    chapter_title VARCHAR,
    character_name VARCHAR,
    status VARCHAR,
    stage VARCHAR,
    progress_percentage INTEGER,
    estimated_completion TIMESTAMP,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    word_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        gj.id,
        gj.trilogy_id,
        gj.sub_chapter_id,
        sc.title AS sub_chapter_title,
        c.title AS chapter_title,
        ch.name AS character_name,
        gj.status,
        gj.stage,
        gj.progress_percentage,
        gj.estimated_completion,
        gj.created_at,
        gj.started_at,
        gj.word_count
    FROM generation_jobs gj
    JOIN sub_chapters sc ON gj.sub_chapter_id = sc.id
    JOIN chapters c ON sc.chapter_id = c.id
    JOIN characters ch ON sc.character_id = ch.id
    WHERE gj.user_id = p_user_id
      AND gj.status IN ('queued', 'in_progress')
    ORDER BY gj.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant access to authenticated users
GRANT EXECUTE ON FUNCTION get_active_generation_jobs(UUID, INTEGER) TO authenticated;

-- Function: Clean up old completed jobs (older than 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_generation_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM generation_jobs
    WHERE status IN ('completed', 'failed', 'cancelled')
      AND completed_at < NOW() - INTERVAL '7 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- PART 8: Comments
-- ============================================================================

COMMENT ON TABLE generation_jobs IS 'Tracks async content generation jobs with real-time progress updates (Epic 10)';
COMMENT ON COLUMN generation_jobs.arq_job_id IS 'Arq (Redis) job ID for tracking in the task queue';
COMMENT ON COLUMN generation_jobs.stage IS 'Human-readable description of current processing stage';
COMMENT ON COLUMN generation_jobs.progress_percentage IS 'Progress from 0-100%';
COMMENT ON COLUMN generation_jobs.estimated_completion IS 'Estimated timestamp when job will complete';
COMMENT ON COLUMN generation_jobs.generation_params IS 'JSONB containing character_id and other generation parameters';

COMMENT ON TABLE user_notification_preferences IS 'User preferences for in-app and email notifications (Epic 10)';
COMMENT ON COLUMN characters.vector_store_collection IS 'ChromaDB collection name for character context (format: {trilogy_id}_character_{character_id})';
COMMENT ON COLUMN characters.vector_store_initialized_at IS 'Timestamp when character vector store was successfully initialized';

-- ============================================================================
-- Migration Complete
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Epic 10: Async Job Queue System - Migration Complete';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Changes applied:';
    RAISE NOTICE '  ✓ Updated generation_jobs table with progress tracking fields';
    RAISE NOTICE '  ✓ Added user_notification_preferences table';
    RAISE NOTICE '  ✓ Updated characters table with vector store status';
    RAISE NOTICE '  ✓ Created indexes for performance optimization';
    RAISE NOTICE '  ✓ Added RLS policies for security';
    RAISE NOTICE '  ✓ Created helper functions for job queries';
    RAISE NOTICE '============================================================================';
END $$;
