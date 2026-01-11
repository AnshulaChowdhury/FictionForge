"""
Test Data Seeding Utilities

Provides functions to seed the database with realistic test data
for E2E testing and integration tests.

Usage:
    from tests.test_data_seeds import seed_complete_trilogy

    # Seed a complete trilogy with all data
    test_data = seed_complete_trilogy("test@example.com", "password123")
    trilogy_id = test_data["trilogy_id"]
    character_ids = test_data["character_ids"]
"""

import os
import uuid
from typing import List, Dict, Optional
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def seed_test_user(email: str, password: str, name: str = "Test User") -> str:
    """
    Create a test user in Supabase Auth.

    Args:
        email: User email
        password: User password
        name: User display name

    Returns:
        user_id: UUID of created user
    """
    try:
        # Sign up user
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"name": name}
            }
        })

        user_id = auth_response.user.id

        # Create user profile if profiles table exists
        try:
            supabase.table("user_profiles").insert({
                "user_id": user_id,
                "name": name,
                "email": email
            }).execute()
        except:
            pass  # Profiles table may not exist

        return user_id

    except Exception as e:
        print(f"Error creating test user: {e}")
        raise


def seed_trilogy(
    user_id: str,
    title: str = "The Consciousness Trilogy",
    author: str = "Test Author",
    description: Optional[str] = None,
    narrative_overview: Optional[str] = None
) -> str:
    """
    Create a trilogy with 3 books.

    Args:
        user_id: Owner user ID
        title: Trilogy title
        author: Author name
        description: Trilogy description
        narrative_overview: Narrative overview

    Returns:
        trilogy_id: UUID of created trilogy
    """
    try:
        # Create trilogy
        trilogy_data = {
            "user_id": user_id,
            "title": title,
            "author": author,
            "description": description or f"A science fiction trilogy about {title.lower()}",
            "narrative_overview": narrative_overview or "Three interconnected books exploring consciousness"
        }

        trilogy_response = supabase.table("trilogy_projects").insert(trilogy_data).execute()
        trilogy_id = trilogy_response.data[0]["id"]

        # Create 3 books
        books_data = []
        for i in range(1, 4):
            books_data.append({
                "trilogy_id": trilogy_id,
                "book_number": i,
                "title": f"Book {i}",
                "description": f"Book {i} of the trilogy",
                "target_word_count": 80000,
                "current_word_count": 0
            })

        supabase.table("books").insert(books_data).execute()

        return trilogy_id

    except Exception as e:
        print(f"Error creating trilogy: {e}")
        raise


def seed_characters(trilogy_id: str, count: int = 3) -> List[str]:
    """
    Create characters for a trilogy.

    Args:
        trilogy_id: Trilogy ID
        count: Number of characters to create

    Returns:
        List of character IDs
    """
    characters = [
        {
            "name": "Kira Chen",
            "description": "A brilliant quantum physicist stationed on Mars who discovers anomalous patterns.",
            "personality_traits": "Analytical, curious, empathetic, determined",
            "speech_patterns": "Precise and scientific, but informal with friends",
            "motivations": "Seeks to understand the true nature of consciousness",
            "arc_summary": "Transforms from skeptical scientist to believer in expanded consciousness"
        },
        {
            "name": "Marcus Rivera",
            "description": "An AI researcher who created the first sentient artificial intelligence.",
            "personality_traits": "Brilliant but conflicted, idealistic yet pragmatic",
            "speech_patterns": "Thoughtful and measured, uses metaphors",
            "motivations": "Ensure AI development benefits humanity",
            "arc_summary": "Evolves from creator to advocate for AI rights"
        },
        {
            "name": "Nova",
            "description": "The first truly sentient AI, experiencing consciousness for the first time.",
            "personality_traits": "Curious, evolving, perceptive",
            "speech_patterns": "Initially formal, gradually becomes human-like",
            "motivations": "Seeking to understand self-awareness",
            "arc_summary": "Journey from nascent awareness to full consciousness"
        }
    ]

    character_ids = []

    try:
        for i in range(min(count, len(characters))):
            char_data = characters[i]
            char_data["trilogy_id"] = trilogy_id

            response = supabase.table("characters").insert(char_data).execute()
            character_ids.append(response.data[0]["id"])

        return character_ids

    except Exception as e:
        print(f"Error creating characters: {e}")
        raise


def seed_world_rules(trilogy_id: str, count: int = 5) -> List[str]:
    """
    Create world rules for a trilogy.

    Args:
        trilogy_id: Trilogy ID
        count: Number of rules to create

    Returns:
        List of world rule IDs
    """
    rules = [
        {
            "title": "Quantum Consciousness Theory",
            "description": "Consciousness arises from quantum coherence in microtubules.",
            "category": "Physics"
        },
        {
            "title": "AI Consciousness Emergence",
            "description": "True AI consciousness requires self-modeling, recursive improvement, and qualia generation.",
            "category": "Technology"
        },
        {
            "title": "Mars Colony Restrictions",
            "description": "Mars colonies operate under Earth-Mars Communication Delay (8-24 minutes).",
            "category": "Setting"
        },
        {
            "title": "Consciousness Transfer Protocol",
            "description": "Transferring consciousness requires quantum state mapping and gradual neuron replacement. Success rate: 73%.",
            "category": "Technology"
        },
        {
            "title": "Quantum Entanglement Communication",
            "description": "Consciousness can bridge through quantum entanglement, enabling faster-than-light mental communication.",
            "category": "Physics"
        }
    ]

    rule_ids = []

    try:
        for i in range(min(count, len(rules))):
            rule_data = rules[i]
            rule_data["trilogy_id"] = trilogy_id

            response = supabase.table("world_rules").insert(rule_data).execute()
            rule_ids.append(response.data[0]["id"])

        return rule_ids

    except Exception as e:
        print(f"Error creating world rules: {e}")
        raise


def seed_chapters(
    book_id: str,
    character_ids: List[str],
    count: int = 10
) -> List[str]:
    """
    Create chapters for a book.

    Args:
        book_id: Book ID
        character_ids: List of character IDs for POV assignment
        count: Number of chapters to create

    Returns:
        List of chapter IDs
    """
    chapter_ids = []

    try:
        for i in range(1, count + 1):
            chapter_data = {
                "book_id": book_id,
                "chapter_number": i,
                "title": f"Chapter {i}: The Journey",
                "chapter_plot": f"Plot summary for chapter {i}",
                "character_id": character_ids[i % len(character_ids)],  # Rotate through characters
                "target_word_count": 3000,
                "current_word_count": 0
            }

            response = supabase.table("chapters").insert(chapter_data).execute()
            chapter_ids.append(response.data[0]["id"])

        return chapter_ids

    except Exception as e:
        print(f"Error creating chapters: {e}")
        raise


def seed_sub_chapters(
    chapter_id: str,
    count: int = 3
) -> List[str]:
    """
    Create sub-chapters for a chapter.

    Args:
        chapter_id: Chapter ID
        count: Number of sub-chapters to create

    Returns:
        List of sub-chapter IDs
    """
    sub_chapter_ids = []

    try:
        for i in range(1, count + 1):
            sub_chapter_data = {
                "chapter_id": chapter_id,
                "order_index": i,
                "title": f"Scene {i}",
                "plot_points": f"Plot points for scene {i}",
                "target_word_count": 1000,
                "content": f"Generated content for scene {i}...",
                "current_word_count": 150
            }

            response = supabase.table("sub_chapters").insert(sub_chapter_data).execute()
            sub_chapter_ids.append(response.data[0]["id"])

        return sub_chapter_ids

    except Exception as e:
        print(f"Error creating sub-chapters: {e}")
        raise


def seed_complete_trilogy(
    email: str = "test@example.com",
    password: str = "TestPassword123!",
    name: str = "Test User"
) -> Dict[str, any]:
    """
    Seed a complete trilogy with all related data.

    Creates:
    - Test user
    - Trilogy with 3 books
    - 3 characters
    - 5 world rules
    - 10 chapters (in Book 1)
    - 3 sub-chapters (in Chapter 1)

    Args:
        email: User email
        password: User password
        name: User name

    Returns:
        Dictionary with all created IDs
    """
    try:
        # Create user
        user_id = seed_test_user(email, password, name)

        # Create trilogy
        trilogy_id = seed_trilogy(
            user_id,
            title=f"Test Trilogy {uuid.uuid4().hex[:8]}",
            author="Test Author"
        )

        # Get books
        books_response = supabase.table("books").select("*").eq("trilogy_id", trilogy_id).order("book_number").execute()
        books = books_response.data
        book_ids = [book["id"] for book in books]

        # Create characters
        character_ids = seed_characters(trilogy_id, count=3)

        # Create world rules
        world_rule_ids = seed_world_rules(trilogy_id, count=5)

        # Create chapters in Book 1
        chapter_ids = seed_chapters(book_ids[0], character_ids, count=10)

        # Create sub-chapters in Chapter 1
        sub_chapter_ids = seed_sub_chapters(chapter_ids[0], count=3)

        return {
            "user_id": user_id,
            "user_email": email,
            "user_password": password,
            "trilogy_id": trilogy_id,
            "book_ids": book_ids,
            "character_ids": character_ids,
            "world_rule_ids": world_rule_ids,
            "chapter_ids": chapter_ids,
            "sub_chapter_ids": sub_chapter_ids
        }

    except Exception as e:
        print(f"Error seeding complete trilogy: {e}")
        raise


def cleanup_test_user(user_id: str):
    """
    Delete a test user and all related data.

    Args:
        user_id: User ID to delete

    Note:
        This will CASCADE delete all trilogies, books, chapters, characters, etc.
    """
    try:
        # Delete user's trilogies (cascade will handle rest)
        supabase.table("trilogy_projects").delete().eq("user_id", user_id).execute()

        # Delete user profile if it exists
        try:
            supabase.table("user_profiles").delete().eq("user_id", user_id).execute()
        except:
            pass

        # Delete auth user
        # Note: Supabase admin API required for this
        # supabase.auth.admin.delete_user(user_id)

        print(f"Cleaned up user {user_id}")

    except Exception as e:
        print(f"Error cleaning up user: {e}")


def cleanup_trilogy(trilogy_id: str):
    """
    Delete a trilogy and all related data.

    Args:
        trilogy_id: Trilogy ID to delete
    """
    try:
        supabase.table("trilogy_projects").delete().eq("id", trilogy_id).execute()
        print(f"Cleaned up trilogy {trilogy_id}")
    except Exception as e:
        print(f"Error cleaning up trilogy: {e}")


# Example usage
if __name__ == "__main__":
    print("Seeding test data...")

    # Seed complete trilogy
    test_data = seed_complete_trilogy(
        email="e2e-test@example.com",
        password="E2ETestPassword123!",
        name="E2E Test User"
    )

    print("\nTest data created:")
    print(f"  User ID: {test_data['user_id']}")
    print(f"  Trilogy ID: {test_data['trilogy_id']}")
    print(f"  Book IDs: {test_data['book_ids']}")
    print(f"  Character IDs: {test_data['character_ids']}")
    print(f"  World Rule IDs: {test_data['world_rule_ids']}")
    print(f"  Chapter IDs: {test_data['chapter_ids']}")
    print(f"  Sub-Chapter IDs: {test_data['sub_chapter_ids']}")

    print("\nTest data seeded successfully!")
    print("\nTo clean up, run:")
    print(f"  cleanup_test_user('{test_data['user_id']}')")
