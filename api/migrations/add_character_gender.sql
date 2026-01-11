-- Migration: Add gender to characters
-- Date: 2025-12-02
-- Description: Adds gender column to characters table for tracking character representation

-- Create enum type for gender (if it doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'character_gender') THEN
        CREATE TYPE character_gender AS ENUM (
            'cisgender_male',
            'cisgender_female',
            'transgender_male',
            'transgender_female',
            'nonbinary'
        );
    END IF;
END$$;

-- Add gender column to characters table
ALTER TABLE characters
ADD COLUMN IF NOT EXISTS gender character_gender;

-- Create index for efficient gender-based queries (useful for analytics)
CREATE INDEX IF NOT EXISTS idx_characters_gender ON characters (gender);
