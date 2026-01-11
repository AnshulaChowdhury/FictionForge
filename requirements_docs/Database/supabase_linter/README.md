# Supabase Database Linter Issues - Remediation Plan

**Generated:** 2025-12-04
**Total Issues:** 27 (9 Security INFO + 18 Performance WARN)

---

## Summary

| Category | Level | Count | Issue Type |
|----------|-------|-------|------------|
| Security | INFO | 9 | RLS enabled but no policies defined |
| Performance | WARN | 18 | `auth.uid()` re-evaluated per row in RLS policies |

---

## Issue 1: RLS Enabled No Policy (Security - INFO)

### Problem
9 tables have Row Level Security enabled but **no RLS policies** defined. This means:
- With RLS enabled and no policies, **all access is denied** by default
- These tables are effectively inaccessible unless using service role key

### Affected Tables

| Table | Status | Recommendation |
|-------|--------|----------------|
| `book_shares` | Future feature | Add placeholder policy |
| `chapter_shares` | Future feature | Add placeholder policy |
| `chapter_share_versions` | Future feature | Add placeholder policy |
| `trilogy_shares` | Future feature | Add placeholder policy |
| `character_change_log` | Future feature | Add placeholder policy |
| `world_rule_change_log` | Future feature | Add placeholder policy |
| `world_rule_books` | Active junction table | Add policy (required) |
| `consistency_alerts` | Future feature | Add placeholder policy |
| `content_review_flags` | Future feature | Add placeholder policy |

### Remediation: Add RLS Policies

For tables reserved for future features, add placeholder policies that enforce user ownership.
These can be refined when the features are implemented.

```sql
-- ============================================
-- Migration: Add RLS Policies for Future Feature Tables
-- Verified against actual schema: 2025-12-04
-- ============================================

-- world_rule_books (active junction table - needs policy now)
CREATE POLICY "Users can manage their own world rule books"
ON world_rule_books
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM world_rules wr
        JOIN trilogy_projects t ON wr.trilogy_id = t.id
        WHERE wr.id = world_rule_books.world_rule_id
        AND t.user_id = (select auth.uid())
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM world_rules wr
        JOIN trilogy_projects t ON wr.trilogy_id = t.id
        WHERE wr.id = world_rule_books.world_rule_id
        AND t.user_id = (select auth.uid())
    )
);

-- trilogy_shares (future: sharing trilogies with other users)
-- Columns: shared_by_user_id (owner), shared_with_email (recipient - email, not user_id)
CREATE POLICY "Users can access their own trilogy shares"
ON trilogy_shares
FOR ALL
USING (
    shared_by_user_id = (select auth.uid())
)
WITH CHECK (
    shared_by_user_id = (select auth.uid())
);

-- book_shares (future: sharing books with other users)
-- Columns: shared_by_user_id (owner), shared_with_email (recipient - email, not user_id)
CREATE POLICY "Users can access their own book shares"
ON book_shares
FOR ALL
USING (
    shared_by_user_id = (select auth.uid())
)
WITH CHECK (
    shared_by_user_id = (select auth.uid())
);

-- chapter_shares (future: sharing chapters with other users)
-- Columns: shared_by_user_id (owner), shared_with_email (recipient - email, not user_id)
CREATE POLICY "Users can access their own chapter shares"
ON chapter_shares
FOR ALL
USING (
    shared_by_user_id = (select auth.uid())
)
WITH CHECK (
    shared_by_user_id = (select auth.uid())
);

-- chapter_share_versions (future: version history for shared chapters)
-- Access via chapter_shares.shared_by_user_id
CREATE POLICY "Users can access their own chapter share versions"
ON chapter_share_versions
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM chapter_shares cs
        WHERE cs.id = chapter_share_versions.chapter_share_id
        AND cs.shared_by_user_id = (select auth.uid())
    )
);

-- character_change_log (future: audit trail for character edits)
-- Columns: character_id, changed_by_user_id
CREATE POLICY "Users can access their own character change logs"
ON character_change_log
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM characters c
        JOIN trilogy_projects t ON c.trilogy_id = t.id
        WHERE c.id = character_change_log.character_id
        AND t.user_id = (select auth.uid())
    )
);

-- world_rule_change_log (future: audit trail for world rule edits)
-- Columns: world_rule_id, changed_by_user_id
CREATE POLICY "Users can access their own world rule change logs"
ON world_rule_change_log
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM world_rules wr
        JOIN trilogy_projects t ON wr.trilogy_id = t.id
        WHERE wr.id = world_rule_change_log.world_rule_id
        AND t.user_id = (select auth.uid())
    )
);

-- consistency_alerts (future: alerts for world rule violations)
-- Columns: sub_chapter_id, world_rule_id (no direct trilogy_id - must join through sub_chapters)
CREATE POLICY "Users can access their own consistency alerts"
ON consistency_alerts
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM sub_chapters sc
        JOIN chapters c ON c.id = sc.chapter_id
        JOIN books b ON b.id = c.book_id
        JOIN trilogy_projects t ON t.id = b.trilogy_id
        WHERE sc.id = consistency_alerts.sub_chapter_id
        AND t.user_id = (select auth.uid())
    )
);

-- content_review_flags (future: flagged content for review)
-- Columns: sub_chapter_id, resolved_by_user_id (no direct trilogy_id - must join through sub_chapters)
CREATE POLICY "Users can access their own content review flags"
ON content_review_flags
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM sub_chapters sc
        JOIN chapters c ON c.id = sc.chapter_id
        JOIN books b ON b.id = c.book_id
        JOIN trilogy_projects t ON t.id = b.trilogy_id
        WHERE sc.id = content_review_flags.sub_chapter_id
        AND t.user_id = (select auth.uid())
    )
);
```

---

## Issue 2: Auth RLS InitPlan (Performance - WARN)

### Problem
18 RLS policies call `auth.uid()` directly, causing the function to be **re-evaluated for every row** scanned. This significantly degrades query performance at scale.

### The Fix
Wrap `auth.uid()` in a subquery: `(select auth.uid())`

This forces PostgreSQL to evaluate the function **once per query** instead of once per row.

**Before (slow):**
```sql
USING (user_id = auth.uid())
```

**After (fast):**
```sql
USING (user_id = (select auth.uid()))
```

### Affected Tables and Policies

#### Priority 1: High-Traffic Tables (Fix First)

| Table | Policy Name | Current Pattern |
|-------|-------------|-----------------|
| `trilogy_projects` | Users can view own projects | `auth.uid()` |
| `trilogy_projects` | Users can create own projects | `auth.uid()` |
| `trilogy_projects` | Users can update own projects | `auth.uid()` |
| `trilogy_projects` | Users can delete own projects | `auth.uid()` |
| `books` | Users can access own books | `auth.uid()` |
| `chapters` | Users can access own chapters | `auth.uid()` |
| `sub_chapters` | Users can access own sub-chapters | `auth.uid()` |
| `characters` | Users can access own characters | `auth.uid()` |

#### Priority 2: Supporting Tables

| Table | Policy Name |
|-------|-------------|
| `sub_chapter_versions` | Users can access own sub-chapter versions |
| `world_rules` | Users can access own world rules |
| `generation_jobs` | generation_jobs_user_isolation |
| `character_book_assignments` | Users can manage their own character book assignments |

#### Priority 3: User Settings Tables

| Table | Policy Name |
|-------|-------------|
| `user_profiles` | Users can view own profile |
| `user_profiles` | Users can update own profile |
| `user_profiles` | Users can insert own profile |
| `user_notification_preferences` | Users can view own notification preferences |
| `user_notification_preferences` | Users can update own notification preferences |
| `user_notification_preferences` | Users can insert own notification preferences |

### Migration Script

```sql
-- ============================================
-- Migration: Fix RLS Performance Issues
-- Date: 2025-12-XX
-- Description: Wrap auth.uid() in subqueries for better performance
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
```

---

## Implementation Checklist

### Phase 1: Add Missing Policies (Security Fixes)
> Schema verified against `current_db` on 2025-12-04

- [ ] Stop the local backend server
- [ ] Run the "Add RLS Policies for Future Feature Tables" migration
- [ ] Verify policies were created in Supabase Dashboard → Authentication → Policies

### Phase 2: Fix Performance Issues
- [ ] Backup current RLS policies (export via Supabase Dashboard or `pg_dump`)
- [ ] Run the performance fix migration (DROP + CREATE policies)
- [ ] Restart the backend server
- [ ] Test all CRUD operations:
  - [ ] Create/read/update/delete trilogy
  - [ ] Create/read/update/delete characters
  - [ ] Create/read/update/delete world rules
  - [ ] Create/read/update/delete chapters
  - [ ] Create/read/update/delete sub-chapters
  - [ ] Generation jobs

### Phase 3: Verify
- [ ] Re-run Supabase linter (Database → Linter)
- [ ] Confirm 0 security issues (INFO)
- [ ] Confirm 0 performance issues (WARN)

---

## References

- [Supabase RLS Performance Best Practices](https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select)
- [Linter: rls_enabled_no_policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
- [Linter: auth_rls_initplan](https://supabase.com/docs/guides/database/database-linter?lint=0003_auth_rls_initplan)
