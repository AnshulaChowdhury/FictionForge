-- Migration: Add character-book assignments
-- Date: 2025-12-02
-- Description: Creates junction table to track which characters appear in which books

-- Create junction table for character-book assignments
CREATE TABLE IF NOT EXISTS character_book_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure a character can only be assigned to a book once
    UNIQUE(character_id, book_id)
);

-- Index for efficient lookups by character
CREATE INDEX IF NOT EXISTS idx_char_book_by_character ON character_book_assignments(character_id);

-- Index for efficient lookups by book (for filtering POV dropdown)
CREATE INDEX IF NOT EXISTS idx_char_book_by_book ON character_book_assignments(book_id);

-- Enable RLS
ALTER TABLE character_book_assignments ENABLE ROW LEVEL SECURITY;

-- RLS policy: Users can only access assignments for characters they own (via trilogy)
CREATE POLICY "Users can manage their own character book assignments"
ON character_book_assignments
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM characters c
        JOIN trilogy_projects t ON c.trilogy_id = t.id
        WHERE c.id = character_book_assignments.character_id
        AND t.user_id = auth.uid()
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM characters c
        JOIN trilogy_projects t ON c.trilogy_id = t.id
        WHERE c.id = character_book_assignments.character_id
        AND t.user_id = auth.uid()
    )
);
