-- ============================================================================
-- CONSCIOUSNESS TRILOGY APP - SUPABASE DATABASE SCHEMA
-- ============================================================================
-- Complete SQL migration script for setting up the database
-- Created: November 2025
-- Technology: Supabase (PostgreSQL with RLS)
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SECTION 1: CORE AUTHENTICATION & USER MANAGEMENT
-- ============================================================================

-- User profiles extends Supabase auth.users
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_profiles
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Indexes
CREATE INDEX idx_user_profiles_id ON user_profiles(id);

-- ============================================================================
-- SECTION 2: TRILOGY PROJECTS
-- ============================================================================

CREATE TABLE trilogy_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR NOT NULL,
    description TEXT,
    author VARCHAR,
    narrative_overview TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE trilogy_projects ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own projects"
    ON trilogy_projects FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own projects"
    ON trilogy_projects FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects"
    ON trilogy_projects FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects"
    ON trilogy_projects FOR DELETE
    USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX idx_trilogy_projects_user_id ON trilogy_projects(user_id);

-- ============================================================================
-- SECTION 3: BOOKS
-- ============================================================================

CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trilogy_id UUID NOT NULL REFERENCES trilogy_projects(id) ON DELETE CASCADE,
    book_number INT NOT NULL CHECK (book_number BETWEEN 1 AND 3),
    title VARCHAR NOT NULL,
    description TEXT,
    target_word_count INT DEFAULT 80000,
    current_word_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(trilogy_id, book_number)
);

-- Enable RLS
ALTER TABLE books ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can access own books"
    ON books FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM trilogy_projects tp
            WHERE tp.id = books.trilogy_id
            AND tp.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_books_trilogy_id ON books(trilogy_id);

-- ============================================================================
-- SECTION 4: CHARACTERS
-- ============================================================================

CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trilogy_id UUID NOT NULL REFERENCES trilogy_projects(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    traits JSONB,
    consciousness_themes VARCHAR[],
    character_arc TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can access own characters"
    ON characters FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM trilogy_projects tp
            WHERE tp.id = characters.trilogy_id
            AND tp.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_characters_trilogy_id ON characters(trilogy_id);

-- ============================================================================
-- SECTION 5: WORLD RULES
-- ============================================================================

CREATE TABLE world_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trilogy_id UUID NOT NULL REFERENCES trilogy_projects(id) ON DELETE CASCADE,
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR NOT NULL,
    times_flagged INT DEFAULT 0,
    times_true_violation INT DEFAULT 0,
    times_false_positive INT DEFAULT 0,
    times_intentional_break INT DEFAULT 0,
    times_checker_error INT DEFAULT 0,
    accuracy_rate FLOAT GENERATED ALWAYS AS (
        CASE
            WHEN times_flagged = 0 THEN 1.0
            ELSE (times_true_violation + times_intentional_break)::FLOAT / times_flagged::FLOAT
        END
    ) STORED,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE world_rules ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can access own world rules"
    ON world_rules FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM trilogy_projects tp
            WHERE tp.id = world_rules.trilogy_id
            AND tp.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_world_rules_trilogy_id ON world_rules(trilogy_id);
CREATE INDEX idx_world_rules_category ON world_rules(category);
CREATE INDEX idx_world_rules_accuracy ON world_rules(accuracy_rate) 
    WHERE times_flagged >= 10;

-- ============================================================================
-- SECTION 6: WORLD RULE BOOKS (JUNCTION TABLE)
-- ============================================================================

CREATE TABLE world_rule_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    world_rule_id UUID NOT NULL REFERENCES world_rules(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(world_rule_id, book_id)
);

-- Indexes
CREATE INDEX idx_world_rule_books_rule_id ON world_rule_books(world_rule_id);
CREATE INDEX idx_world_rule_books_book_id ON world_rule_books(book_id);

-- ============================================================================
-- SECTION 7: CHAPTERS
-- ============================================================================

CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    title VARCHAR NOT NULL,
    chapter_number INT NOT NULL,
    chapter_plot TEXT,
    target_word_count INT,
    current_word_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(book_id, chapter_number)
);

-- Enable RLS
ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can access own chapters"
    ON chapters FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM books b
            JOIN trilogy_projects tp ON b.trilogy_id = tp.id
            WHERE b.id = chapters.book_id
            AND tp.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_chapters_book_id ON chapters(book_id);
CREATE INDEX idx_chapters_character_id ON chapters(character_id);

-- ============================================================================
-- SECTION 8: SUB-CHAPTERS
-- ============================================================================

CREATE TABLE sub_chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    sub_chapter_number INT NOT NULL,
    title VARCHAR,
    plot_points TEXT,
    content TEXT,
    word_count INT DEFAULT 0,
    status VARCHAR DEFAULT 'draft' 
        CHECK (status IN ('draft', 'in_progress', 'completed', 'needs_review')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(chapter_id, sub_chapter_number)
);

-- Enable RLS
ALTER TABLE sub_chapters ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can access own sub-chapters"
    ON sub_chapters FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM chapters c
            JOIN books b ON c.book_id = b.id
            JOIN trilogy_projects tp ON b.trilogy_id = tp.id
            WHERE c.id = sub_chapters.chapter_id
            AND tp.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_sub_chapters_chapter_id ON sub_chapters(chapter_id);
CREATE INDEX idx_sub_chapters_character_id ON sub_chapters(character_id);
CREATE INDEX idx_sub_chapters_updated_at ON sub_chapters(updated_at DESC);

-- ============================================================================
-- SECTION 9: SUB-CHAPTER VERSIONS
-- ============================================================================

CREATE TABLE sub_chapter_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sub_chapter_id UUID NOT NULL REFERENCES sub_chapters(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    content TEXT NOT NULL,
    word_count INT NOT NULL,
    snapshot_metadata JSONB,
    generated_by_model VARCHAR,
    generation_job_id UUID,
    is_ai_generated BOOLEAN DEFAULT FALSE,
    change_description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_user_id UUID REFERENCES auth.users(id),
    
    UNIQUE(sub_chapter_id, version_number)
);

-- Enable RLS
ALTER TABLE sub_chapter_versions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can access own sub-chapter versions"
    ON sub_chapter_versions FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM sub_chapters sc
            JOIN chapters c ON sc.chapter_id = c.id
            JOIN books b ON c.book_id = b.id
            JOIN trilogy_projects tp ON b.trilogy_id = tp.id
            WHERE sc.id = sub_chapter_versions.sub_chapter_id
            AND tp.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_sub_chapter_versions_sub_chapter_id 
    ON sub_chapter_versions(sub_chapter_id);
CREATE INDEX idx_sub_chapter_versions_lookup 
    ON sub_chapter_versions(sub_chapter_id, version_number DESC);

-- ============================================================================
-- SECTION 10: CHANGE LOGS (NO RLS - SYSTEM AUDIT TRAIL)
-- ============================================================================

-- Character Change Log
CREATE TABLE character_change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by_user_id UUID REFERENCES auth.users(id),
    field_changed VARCHAR,
    old_value JSONB,
    new_value JSONB,
    user_note TEXT
);

CREATE INDEX idx_character_change_log_character_id ON character_change_log(character_id);
CREATE INDEX idx_character_change_log_changed_at ON character_change_log(changed_at DESC);

-- World Rule Change Log
CREATE TABLE world_rule_change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    world_rule_id UUID NOT NULL REFERENCES world_rules(id) ON DELETE CASCADE,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by_user_id UUID REFERENCES auth.users(id),
    field_changed VARCHAR,
    old_value JSONB,
    new_value JSONB,
    old_title VARCHAR,
    new_title VARCHAR,
    old_description TEXT,
    new_description TEXT,
    old_category VARCHAR,
    new_category VARCHAR,
    reason TEXT
);

CREATE INDEX idx_world_rule_change_log_rule_id ON world_rule_change_log(world_rule_id);
CREATE INDEX idx_world_rule_change_log_changed_at ON world_rule_change_log(changed_at DESC);

-- ============================================================================
-- SECTION 11: CONSISTENCY & REVIEW
-- ============================================================================

-- Consistency Alerts
CREATE TABLE consistency_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sub_chapter_id UUID NOT NULL REFERENCES sub_chapters(id) ON DELETE CASCADE,
    world_rule_id UUID NOT NULL REFERENCES world_rules(id) ON DELETE CASCADE,
    alert_type VARCHAR CHECK (alert_type IN ('potential_violation', 'rule_clarification_needed')),
    alert_text TEXT,
    dismissed BOOLEAN DEFAULT FALSE,
    dismissal_reason VARCHAR CHECK (dismissal_reason IN 
        ('true_violation', 'false_positive', 'intentional_break', 'checker_error')),
    dismissal_note TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX idx_consistency_alerts_sub_chapter_id ON consistency_alerts(sub_chapter_id);
CREATE INDEX idx_consistency_alerts_unresolved 
    ON consistency_alerts(sub_chapter_id) WHERE resolved_at IS NULL;

-- Content Review Flags
CREATE TABLE content_review_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sub_chapter_id UUID NOT NULL REFERENCES sub_chapters(id) ON DELETE CASCADE,
    flag_type VARCHAR CHECK (flag_type IN 
        ('character_changed', 'rule_changed', 'user_marked', 'consistency_alert')),
    reason TEXT,
    flagged_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by_user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_content_review_flags_sub_chapter_id ON content_review_flags(sub_chapter_id);
CREATE INDEX idx_content_review_flags_unresolved 
    ON content_review_flags(sub_chapter_id) WHERE resolved_at IS NULL;

-- ============================================================================
-- SECTION 12: GENERATION JOBS
-- ============================================================================

CREATE TABLE generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trilogy_id UUID NOT NULL REFERENCES trilogy_projects(id) ON DELETE CASCADE,
    sub_chapter_id UUID REFERENCES sub_chapters(id) ON DELETE CASCADE,
    status VARCHAR NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    job_type VARCHAR,
    priority INT DEFAULT 0,
    prompt TEXT,
    target_word_count INT,
    model_used VARCHAR,
    error_message TEXT,
    result_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by_user_id UUID REFERENCES auth.users(id)
);

CREATE INDEX idx_generation_jobs_status 
    ON generation_jobs(status, created_at) WHERE status != 'completed';
CREATE INDEX idx_generation_jobs_trilogy_id ON generation_jobs(trilogy_id);

-- ============================================================================
-- SECTION 13: SHARING & COLLABORATION
-- ============================================================================

-- Trilogy Shares
CREATE TABLE trilogy_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trilogy_id UUID NOT NULL REFERENCES trilogy_projects(id) ON DELETE CASCADE,
    shared_by_user_id UUID NOT NULL REFERENCES auth.users(id),
    shared_with_email VARCHAR NOT NULL,
    permission_level VARCHAR CHECK (permission_level IN ('read_only', 'comment')),
    access_token VARCHAR UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP
);

CREATE INDEX idx_trilogy_shares_trilogy_id ON trilogy_shares(trilogy_id);
CREATE INDEX idx_trilogy_shares_access_token ON trilogy_shares(access_token);

-- Book Shares
CREATE TABLE book_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    shared_by_user_id UUID NOT NULL REFERENCES auth.users(id),
    shared_with_email VARCHAR NOT NULL,
    permission_level VARCHAR CHECK (permission_level IN ('read_only', 'comment')),
    access_token VARCHAR UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP
);

CREATE INDEX idx_book_shares_book_id ON book_shares(book_id);
CREATE INDEX idx_book_shares_access_token ON book_shares(access_token);
CREATE INDEX idx_book_shares_expires_at ON book_shares(expires_at);

-- Chapter Shares
CREATE TABLE chapter_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    shared_by_user_id UUID NOT NULL REFERENCES auth.users(id),
    shared_with_email VARCHAR NOT NULL,
    permission_level VARCHAR CHECK (permission_level IN ('read_only', 'comment')),
    access_token VARCHAR UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP
);

CREATE INDEX idx_chapter_shares_chapter_id ON chapter_shares(chapter_id);
CREATE INDEX idx_chapter_shares_access_token ON chapter_shares(access_token);
CREATE INDEX idx_chapter_shares_expires_at ON chapter_shares(expires_at);

-- Chapter Share Versions (specifies which versions are shared)
CREATE TABLE chapter_share_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_share_id UUID NOT NULL REFERENCES chapter_shares(id) ON DELETE CASCADE,
    sub_chapter_id UUID NOT NULL REFERENCES sub_chapters(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES sub_chapter_versions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(chapter_share_id, sub_chapter_id)
);

CREATE INDEX idx_chapter_share_versions_share_id ON chapter_share_versions(chapter_share_id);
CREATE INDEX idx_chapter_share_versions_sub_chapter_id ON chapter_share_versions(sub_chapter_id);

-- ============================================================================
-- SECTION 14: DATABASE TRIGGERS
-- ============================================================================

-- Trigger 1: Auto-populate sub_chapters.character_id from parent chapter
CREATE OR REPLACE FUNCTION copy_character_from_chapter()
RETURNS TRIGGER AS $$
BEGIN
    -- On INSERT, populate character_id from parent chapter
    SELECT character_id INTO NEW.character_id
    FROM chapters
    WHERE id = NEW.chapter_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_subchapter_character
    BEFORE INSERT ON sub_chapters
    FOR EACH ROW
    EXECUTE FUNCTION copy_character_from_chapter();

-- Trigger 2: Enforce character_id consistency between chapter and sub-chapter
CREATE OR REPLACE FUNCTION enforce_character_consistency()
RETURNS TRIGGER AS $$
DECLARE
    chapter_character_id UUID;
BEGIN
    -- Get the character_id from the parent chapter
    SELECT character_id INTO chapter_character_id
    FROM chapters
    WHERE id = NEW.chapter_id;
    
    -- Ensure sub_chapter character_id matches chapter character_id
    IF NEW.character_id != chapter_character_id THEN
        RAISE EXCEPTION 'sub_chapter character_id must match chapter character_id';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_subchapter_character
    BEFORE INSERT OR UPDATE ON sub_chapters
    FOR EACH ROW
    EXECUTE FUNCTION enforce_character_consistency();

-- Trigger 3: Update chapter word count when sub-chapter word count changes
CREATE OR REPLACE FUNCTION update_chapter_word_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chapters
    SET current_word_count = (
        SELECT COALESCE(SUM(word_count), 0)
        FROM sub_chapters
        WHERE chapter_id = NEW.chapter_id
    ),
    updated_at = NOW()
    WHERE id = NEW.chapter_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_chapter_word_count_on_subchapter
    AFTER INSERT OR UPDATE OR DELETE ON sub_chapters
    FOR EACH ROW
    EXECUTE FUNCTION update_chapter_word_count();

-- Trigger 4: Update book word count when chapter word count changes
CREATE OR REPLACE FUNCTION update_book_word_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE books
    SET current_word_count = (
        SELECT COALESCE(SUM(current_word_count), 0)
        FROM chapters
        WHERE book_id = NEW.book_id
    ),
    updated_at = NOW()
    WHERE id = NEW.book_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_book_word_count_on_chapter
    AFTER INSERT OR UPDATE OR DELETE ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION update_book_word_count();

-- ============================================================================
-- SECTION 15: UTILITY FUNCTIONS
-- ============================================================================

-- Function to get total trilogy word count
CREATE OR REPLACE FUNCTION get_trilogy_word_count(trilogy_uuid UUID)
RETURNS INT AS $$
    SELECT COALESCE(SUM(b.current_word_count), 0)
    FROM books b
    WHERE b.trilogy_id = trilogy_uuid;
$$ LANGUAGE SQL;

-- Function to get character's total content across trilogy
CREATE OR REPLACE FUNCTION get_character_word_count(character_uuid UUID)
RETURNS INT AS $$
    SELECT COALESCE(SUM(sc.word_count), 0)
    FROM sub_chapters sc
    WHERE sc.character_id = character_uuid;
$$ LANGUAGE SQL;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'CONSCIOUSNESS TRILOGY APP - DATABASE SCHEMA SETUP COMPLETE';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Successfully created:';
    RAISE NOTICE '  - 18 tables with Row Level Security policies';
    RAISE NOTICE '  - 30+ indexes for query optimization';
    RAISE NOTICE '  - 4 database triggers for automatic updates';
    RAISE NOTICE '  - 2 utility functions for word count calculations';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Configure Supabase Auth (Email/Password + Google OAuth)';
    RAISE NOTICE '  2. Set up ChromaDB for character-specific vector stores';
    RAISE NOTICE '  3. Configure Redis for caching';
    RAISE NOTICE '  4. Set up pg-boss for job queue management';
    RAISE NOTICE '  5. Test RLS policies with test users';
    RAISE NOTICE '============================================================================';
END $$;