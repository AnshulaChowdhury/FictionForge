"""
Unit tests for ChapterManager service (Epic 4).

Tests cover:
- Successful chapter creation with auto-numbering
- Get operations (single and list)
- Update operations
- Delete operations with renumbering
- Chapter reordering
- Progress calculations
- Error handling and validation
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from api.services.chapter_manager import (
    ChapterManager,
    ChapterCreationError,
    ChapterNotFoundError,
    ChapterUpdateError,
    ChapterDeletionError,
    ChapterReorderError,
)
from api.models.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
)
from postgrest.exceptions import APIError


class TestChapterManagerCreate:
    """Tests for ChapterManager.create_chapter()"""

    @pytest.mark.asyncio
    async def test_create_chapter_success(
        self, mock_user_id, mock_book_ids, mock_character_id, sample_chapter_data
    ):
        """Test successful chapter creation with auto chapter_number."""
        # Arrange
        request = ChapterCreate(
            book_id=mock_book_ids[0],
            character_id=mock_character_id,
            title="The Awakening",
            description="Sarah discovers the quantum consciousness lab",
            target_word_count=3000,
        )

        mock_client = MagicMock()

        # Mock book ownership verification
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_user_id}
        }]

        # Mock character ownership verification
        char_mock = MagicMock()
        book_response_data = [{"trilogy_id": "660e8400-e29b-41d4-a716-446655440001"}]
        char_response_data = [{
            "id": mock_character_id,
            "trilogy_id": "660e8400-e29b-41d4-a716-446655440001"
        }]

        # Mock next chapter number (no existing chapters = 1)
        next_num_mock = MagicMock()
        next_num_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        # Mock chapter insert
        chapters_insert_mock = MagicMock()
        chapters_insert_mock.insert.return_value.execute.return_value.data = [sample_chapter_data]

        call_count = {"books": 0, "characters": 0, "chapters": 0}
        def table_side_effect(table_name):
            if table_name == "books":
                call_count["books"] += 1
                if call_count["books"] == 1:
                    return book_mock
                else:
                    # For character verification
                    books_select = MagicMock()
                    books_select.select.return_value.eq.return_value.execute.return_value.data = book_response_data
                    return books_select
            elif table_name == "characters":
                char_select = MagicMock()
                char_select.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = char_response_data
                return char_select
            elif table_name == "chapters":
                call_count["chapters"] += 1
                if call_count["chapters"] == 1:
                    return next_num_mock
                else:
                    return chapters_insert_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.create_chapter(request)

            # Assert
            assert isinstance(response, ChapterResponse)
            assert response.title == "The Awakening"
            assert response.chapter_number == 1
            assert response.target_word_count == 3000

    @pytest.mark.asyncio
    async def test_create_chapter_minimal_fields(
        self, mock_user_id, mock_book_ids, mock_character_id, mock_chapter_id
    ):
        """Test chapter creation with only required fields."""
        # Arrange
        request = ChapterCreate(
            book_id=mock_book_ids[0],
            character_id=mock_character_id,
            title="Chapter Title",
        )

        minimal_chapter_data = {
            "id": mock_chapter_id,
            "book_id": mock_book_ids[0],
            "character_id": mock_character_id,
            "title": "Chapter Title",
            "chapter_number": 1,
            "description": None,
            "target_word_count": None,
            "current_word_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        mock_client = MagicMock()

        # Setup mocks similar to above
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_user_id}
        }]

        book_response_data = [{"trilogy_id": "660e8400-e29b-41d4-a716-446655440001"}]
        char_response_data = [{
            "id": mock_character_id,
            "trilogy_id": "660e8400-e29b-41d4-a716-446655440001"
        }]

        next_num_mock = MagicMock()
        next_num_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        chapters_insert_mock = MagicMock()
        chapters_insert_mock.insert.return_value.execute.return_value.data = [minimal_chapter_data]

        call_count = {"books": 0, "chapters": 0}
        def table_side_effect(table_name):
            if table_name == "books":
                call_count["books"] += 1
                if call_count["books"] == 1:
                    return book_mock
                else:
                    books_select = MagicMock()
                    books_select.select.return_value.eq.return_value.execute.return_value.data = book_response_data
                    return books_select
            elif table_name == "characters":
                char_select = MagicMock()
                char_select.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = char_response_data
                return char_select
            elif table_name == "chapters":
                call_count["chapters"] += 1
                return next_num_mock if call_count["chapters"] == 1 else chapters_insert_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.create_chapter(request)

            # Assert
            assert response.title == "Chapter Title"
            assert response.description is None
            assert response.target_word_count is None


class TestChapterManagerGet:
    """Tests for ChapterManager get operations"""

    @pytest.mark.asyncio
    async def test_get_book_chapters_success(
        self, mock_user_id, mock_book_ids, sample_chapter_data
    ):
        """Test retrieving all chapters for a book."""
        # Arrange
        mock_client = MagicMock()

        # Mock book ownership verification
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_user_id}
        }]

        # Mock chapters query
        chapters_mock = MagicMock()
        chapters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_chapter_data
        ]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "books":
                return book_mock
            elif table_name == "chapters":
                return chapters_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.get_book_chapters(mock_book_ids[0])

            # Assert
            assert response.total == 1
            assert len(response.chapters) == 1
            assert response.chapters[0].title == "The Awakening"

    @pytest.mark.asyncio
    async def test_get_chapter_success(
        self, mock_user_id, mock_chapter_id, sample_chapter_data
    ):
        """Test retrieving a single chapter."""
        # Arrange
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_user_id}
            }
        }

        mock_client = MagicMock()
        chapters_mock = MagicMock()
        chapters_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        mock_client.table.return_value = chapters_mock

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.get_chapter(mock_chapter_id)

            # Assert
            assert response.id == mock_chapter_id
            assert response.title == "The Awakening"


class TestChapterManagerUpdate:
    """Tests for ChapterManager.update_chapter()"""

    @pytest.mark.asyncio
    async def test_update_chapter_success(
        self, mock_user_id, mock_chapter_id, sample_chapter_data
    ):
        """Test successful chapter update."""
        # Arrange
        request = ChapterUpdate(
            title="Updated Title",
            description="Updated description"
        )

        updated_data = {
            **sample_chapter_data,
            "title": "Updated Title",
            "description": "Updated description"
        }

        mock_client = MagicMock()

        # Mock get_chapter
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_user_id}
            }
        }
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        # Mock update
        update_mock = MagicMock()
        update_mock.update.return_value.eq.return_value.execute.return_value.data = [updated_data]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "chapters":
                call_count[0] += 1
                return select_mock if call_count[0] == 1 else update_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.update_chapter(mock_chapter_id, request)

            # Assert
            assert response.title == "Updated Title"
            assert response.description == "Updated description"


class TestChapterManagerDelete:
    """Tests for ChapterManager.delete_chapter()"""

    @pytest.mark.asyncio
    async def test_delete_chapter_success(
        self, mock_user_id, mock_chapter_id, sample_chapter_data
    ):
        """Test successful chapter deletion."""
        # Arrange
        mock_client = MagicMock()

        # Mock get_chapter
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_user_id}
            }
        }
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        # Mock delete
        delete_mock = MagicMock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value.data = [sample_chapter_data]

        # Mock renumbering query (no chapters after this one)
        renumber_mock = MagicMock()
        renumber_mock.select.return_value.eq.return_value.gt.return_value.execute.return_value.data = []

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "chapters":
                call_count[0] += 1
                if call_count[0] == 1:
                    return select_mock
                elif call_count[0] == 2:
                    return delete_mock
                else:
                    return renumber_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.delete_chapter(mock_chapter_id)

            # Assert
            assert response.id == mock_chapter_id
            assert "deleted successfully" in response.message


class TestChapterManagerReorder:
    """Tests for ChapterManager.reorder_chapter()"""

    @pytest.mark.asyncio
    async def test_reorder_chapter_down(
        self, mock_user_id, mock_book_ids, mock_chapter_id
    ):
        """Test moving a chapter down (1 -> 3)."""
        # Arrange
        # Create 3 chapters
        chapters_data = [
            {
                "id": f"ch{i}",
                "book_id": mock_book_ids[0],
                "character_id": "char1",
                "title": f"Chapter {i}",
                "chapter_number": i,
                "target_word_count": 3000,
                "current_word_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            for i in range(1, 4)
        ]

        mock_client = MagicMock()

        # Mock get_chapter (for ch1)
        chapter_with_book = {
            **chapters_data[0],
            "books": {
                "trilogy_projects": {"user_id": mock_user_id}
            }
        }
        get_chapter_mock = MagicMock()
        get_chapter_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        # Mock book ownership
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_user_id}
        }]

        # Mock get_book_chapters
        chapters_list_mock = MagicMock()
        chapters_list_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = chapters_data

        # Mock updates
        update_mock = MagicMock()
        update_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        # Mock final get_book_chapters call (returns updated list)
        final_chapters_mock = MagicMock()
        final_chapters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = chapters_data

        call_count = {"chapters": 0, "books": 0}
        def table_side_effect(table_name):
            if table_name == "books":
                # All books table calls return book_mock for ownership verification
                return book_mock
            elif table_name == "chapters":
                call_count["chapters"] += 1
                if call_count["chapters"] == 1:
                    return get_chapter_mock  # get_chapter for the chapter to move
                elif call_count["chapters"] == 2:
                    return chapters_list_mock  # First get_book_chapters for reorder logic
                elif call_count["chapters"] >= 3 and call_count["chapters"] <= 5:
                    return update_mock  # Updates for 3 chapters
                else:
                    return final_chapters_mock  # Final get_book_chapters call

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.chapter_manager.supabase", mock_client):
            manager = ChapterManager(user_id=mock_user_id)

            # Act
            response = await manager.reorder_chapter("ch1", 3)

            # Assert - should return updated list
            assert response.total == 3
