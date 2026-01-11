# Character Enhancements: Book Assignments Feature

## Overview

This feature allows users to specify which books in a trilogy each character appears in. Characters can be assigned to one or more books, enabling:
- Filtering POV character selection by book when creating chapters
- Tracking character presence across the trilogy timeline
- Better organization of character involvement in multi-book narratives

## Requirements

### User Story
As a trilogy author, I want to specify which books each character appears in, so that I can track character involvement across my trilogy and filter character lists when working on specific books.

### Acceptance Criteria
1. When creating a character, users can select which books the character appears in via checkboxes
2. When editing a character, users can modify the book assignments
3. Book selection checkboxes should match the visual style of the World Rule form
4. Character book assignments persist across sessions
5. The API supports filtering characters by book for POV selection

## Technical Implementation

### Database Layer

**Table: `character_book_assignments`**
- Location: `api/migrations/add_character_book_assignments.sql`
- Junction table linking characters to books (many-to-many)

```sql
CREATE TABLE character_book_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(character_id, book_id)
);
```

**Indexes:**
- `idx_char_book_by_character` - Efficient lookups by character
- `idx_char_book_by_book` - Efficient lookups by book (for POV filtering)

**Row-Level Security:**
- Users can only access assignments for characters they own (via trilogy ownership)

### Backend API Layer

**Models (`api/models/character.py`):**
- `CharacterCreate.book_ids: List[str]` - Book IDs for new characters
- `CharacterUpdate.book_ids: Optional[List[str]]` - Book IDs for updates
- `CharacterResponse.book_ids: List[str]` - Book IDs in response

**Service (`api/services/character_manager.py`):**
- `_get_character_book_ids(character_id)` - Fetches book assignments
- `_set_character_book_ids(character_id, book_ids)` - Updates assignments (delete + insert)
- `get_characters_by_book(book_id)` - Returns characters assigned to a specific book

**Routes (`api/routes/character.py`):**
- `GET /api/characters/book/{book_id}` - List characters for a specific book

### Frontend Layer

**API Types (`frontend/src/api/characters.ts`):**
- `Character.book_ids: string[]`
- `CreateCharacterRequest.book_ids?: string[]`
- `UpdateCharacterRequest.book_ids?: string[]`

**UI Components (`frontend/src/pages/CharactersPage.tsx`):**
- Book checkboxes in Create Character dialog
- Book checkboxes in Edit Character dialog
- Query to fetch trilogy books for checkbox labels
- Form state for `selectedBookIds`

### UI Design Reference

The book selection checkboxes should match the pattern used in `WorldRuleForm.tsx`:

```tsx
<div className="space-y-3">
  <Label>Appears in Books</Label>
  <p className="text-sm text-muted-foreground">
    Select which books this character appears in.
  </p>
  <div className="space-y-2">
    {books.map((book) => (
      <div key={book.id} className="flex items-center space-x-2">
        <Checkbox
          id={`book-${book.id}`}
          checked={selectedBookIds.includes(book.id)}
          onCheckedChange={() => toggleBookSelection(book.id)}
        />
        <label
          htmlFor={`book-${book.id}`}
          className="text-sm font-medium leading-none cursor-pointer"
        >
          Book {book.book_number}: {book.title}
        </label>
      </div>
    ))}
  </div>
</div>
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Database migration | ✅ Complete |
| RLS policies | ✅ Complete |
| Backend Pydantic models | ✅ Complete |
| Backend CharacterManager service | ✅ Complete |
| Backend API routes | ✅ Complete |
| Frontend API types | ✅ Complete |
| Frontend Create dialog UI | ✅ Complete |
| Frontend Edit dialog UI | ✅ Complete |

**Feature fully implemented on 2025-12-04**

## Dependencies

- Radix UI Checkbox component (`@/components/ui/checkbox`)
- Books API for fetching trilogy books (`@/api/trilogy` - `getTrilogyBooks`)

## Testing Considerations

1. Create character with book assignments - verify assignments saved
2. Edit character book assignments - verify changes persist
3. Remove all book assignments - verify character still valid
4. Delete book - verify cascade deletes assignments
5. Delete character - verify cascade deletes assignments
6. RLS - verify users cannot see other users' character assignments
