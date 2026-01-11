-- ============================================
-- Migration: Fix RLS Performance Issues (Issue 2)
-- Date: 2025-12-17
-- Description: Wrap auth.uid() in subqueries for better performance
-- Reference: requirements_docs/Database/supabase_linter/README.md
-- ============================================
--
-- PROBLEM: 18 RLS policies call auth.uid() directly, causing the function
-- to be re-evaluated for every row scanned.
--
-- FIX: Wrap auth.uid() in a subquery: (select auth.uid())
-- This forces PostgreSQL to evaluate the function ONCE per query.
--
-- AFFECTED TABLES:
-- - user_profiles (3 policies)
-- - trilogy_projects (4 policies)
-- - books (1 policy)
-- - characters (1 policy)
-- - world_rules (1 policy)
-- - chapters (1 policy)
-- - sub_chapters (1 policy)
-- - sub_chapter_versions (1 policy)
-- - generation_jobs (1 policy)
-- - user_notification_preferences (3 policies)
-- - character_book_assignments (1 policy)
-- ============================================

-- IMPORTANT: Run these in a transaction
BEGIN;

-- ============================================
-- user_profiles
-- ============================================
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (id = (select auth.uid()));

-- ============================================
-- trilogy_projects
-- ============================================
DROP POLICY IF EXISTS "Users can view own projects" ON trilogy_projects;
CREATE POLICY "Users can view own projects" ON trilogy_projects
    FOR SELECT USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can create own projects" ON trilogy_projects;
CREATE POLICY "Users can create own projects" ON trilogy_projects
    FOR INSERT WITH CHECK (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can update own projects" ON trilogy_projects;
CREATE POLICY "Users can update own projects" ON trilogy_projects
    FOR UPDATE USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can delete own projects" ON trilogy_projects;
CREATE POLICY "Users can delete own projects" ON trilogy_projects
    FOR DELETE USING (user_id = (select auth.uid()));

-- ============================================
-- books
-- ============================================
DROP POLICY IF EXISTS "Users can access own books" ON books;
CREATE POLICY "Users can access own books" ON books
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM trilogy_projects t
            WHERE t.id = books.trilogy_id
            AND t.user_id = (select auth.uid())
        )
    );

-- ============================================
-- characters
-- ============================================
DROP POLICY IF EXISTS "Users can access own characters" ON characters;
CREATE POLICY "Users can access own characters" ON characters
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM trilogy_projects t
            WHERE t.id = characters.trilogy_id
            AND t.user_id = (select auth.uid())
        )
    );

-- ============================================
-- world_rules
-- ============================================
DROP POLICY IF EXISTS "Users can access own world rules" ON world_rules;
CREATE POLICY "Users can access own world rules" ON world_rules
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM trilogy_projects t
            WHERE t.id = world_rules.trilogy_id
            AND t.user_id = (select auth.uid())
        )
    );

-- ============================================
-- chapters
-- ============================================
DROP POLICY IF EXISTS "Users can access own chapters" ON chapters;
CREATE POLICY "Users can access own chapters" ON chapters
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM books b
            JOIN trilogy_projects t ON t.id = b.trilogy_id
            WHERE b.id = chapters.book_id
            AND t.user_id = (select auth.uid())
        )
    );

-- ============================================
-- sub_chapters
-- ============================================
DROP POLICY IF EXISTS "Users can access own sub-chapters" ON sub_chapters;
CREATE POLICY "Users can access own sub-chapters" ON sub_chapters
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM chapters c
            JOIN books b ON b.id = c.book_id
            JOIN trilogy_projects t ON t.id = b.trilogy_id
            WHERE c.id = sub_chapters.chapter_id
            AND t.user_id = (select auth.uid())
        )
    );

-- ============================================
-- sub_chapter_versions
-- ============================================
DROP POLICY IF EXISTS "Users can access own sub-chapter versions" ON sub_chapter_versions;
CREATE POLICY "Users can access own sub-chapter versions" ON sub_chapter_versions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM sub_chapters sc
            JOIN chapters c ON c.id = sc.chapter_id
            JOIN books b ON b.id = c.book_id
            JOIN trilogy_projects t ON t.id = b.trilogy_id
            WHERE sc.id = sub_chapter_versions.sub_chapter_id
            AND t.user_id = (select auth.uid())
        )
    );

-- ============================================
-- generation_jobs
-- ============================================
DROP POLICY IF EXISTS "generation_jobs_user_isolation" ON generation_jobs;
CREATE POLICY "generation_jobs_user_isolation" ON generation_jobs
    FOR ALL USING (user_id = (select auth.uid()));

-- ============================================
-- user_notification_preferences
-- ============================================
DROP POLICY IF EXISTS "Users can view own notification preferences" ON user_notification_preferences;
CREATE POLICY "Users can view own notification preferences" ON user_notification_preferences
    FOR SELECT USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can update own notification preferences" ON user_notification_preferences;
CREATE POLICY "Users can update own notification preferences" ON user_notification_preferences
    FOR UPDATE USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "Users can insert own notification preferences" ON user_notification_preferences;
CREATE POLICY "Users can insert own notification preferences" ON user_notification_preferences
    FOR INSERT WITH CHECK (user_id = (select auth.uid()));

-- ============================================
-- character_book_assignments
-- ============================================
DROP POLICY IF EXISTS "Users can manage their own character book assignments" ON character_book_assignments;
CREATE POLICY "Users can manage their own character book assignments" ON character_book_assignments
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM characters c
            JOIN trilogy_projects t ON c.trilogy_id = t.id
            WHERE c.id = character_book_assignments.character_id
            AND t.user_id = (select auth.uid())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM characters c
            JOIN trilogy_projects t ON c.trilogy_id = t.id
            WHERE c.id = character_book_assignments.character_id
            AND t.user_id = (select auth.uid())
        )
    );

COMMIT;
