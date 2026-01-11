"""
Unit tests for SubChapterManager service (Epic 6).

Tests sub-chapter creation, retrieval, updates, and deletion operations.
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.sub_chapter_manager import SubChapterManager
from api.models.sub_chapter import (
    SubChapterCreate,
    SubChapterUpdate,
    SubChapter,
    SubChapterCreateResponse,
    SubChapterStatus
)


@pytest.fixture
def manager():
    """Create SubChapterManager instance with mocked dependencies."""
    manager = SubChapterManager()
    manager.supabase = MagicMock()
    return manager


@pytest.fixture
def sample_chapter_data():
    """Sample chapter data for testing."""
    return {
        "id": str(uuid4()),
        "book_id": str(uuid4()),
        "character_id": str(uuid4()),
        "book": {
            "id": str(uuid4()),
            "trilogy_id": str(uuid4()),
            "trilogy": {
                "user_id": str(uuid4())
            }
        }
    }


@pytest.fixture
def sample_sub_chapter_data():
    """Sample sub-chapter data for testing."""
    return {
        "id": str(uuid4()),
        "chapter_id": str(uuid4()),
        "character_id": str(uuid4()),
        "sub_chapter_number": 1,
        "title": "Test Sub-Chapter",
        "plot_points": "Character discovers important clue",
        "content": None,
        "word_count": 0,
        "status": SubChapterStatus.DRAFT,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


class TestSubChapterCreation:
    """Tests for sub-chapter creation."""

    @pytest.mark.asyncio
    async def test_create_sub_chapter_success(self, manager, sample_chapter_data):
        """Test successful sub-chapter creation without generation."""
        # Arrange
        chapter_id = UUID(sample_chapter_data["id"])
        user_id = uuid4()

        data = SubChapterCreate(
            chapter_id=chapter_id,
            title="Test Sub-Chapter",
            plot_points="Test plot points",
            target_word_count=2000
        )

        # Mock chapter lookup
        manager.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_chapter_data]
        )

        # Mock next sub_chapter_number lookup
        manager.supabase.rpc.return_value.execute.return_value = MagicMock(data=1)

        # Mock sub-chapter insertion
        created_sub_chapter = {
            "id": str(uuid4()),
            "chapter_id": str(chapter_id),
            "character_id": sample_chapter_data["character_id"],
            "sub_chapter_number": 1,
            "title": data.title,
            "plot_points": data.plot_points,
            "target_word_count": data.target_word_count,
            "status": SubChapterStatus.DRAFT,
            "word_count": 0
        }

        # Create a chain of mocked calls for insert
        insert_mock = MagicMock()
        insert_mock.execute.return_value = MagicMock(data=[created_sub_chapter])
        manager.supabase.table.return_value.insert.return_value = insert_mock

        # Act
        result = await manager.create_sub_chapter(data, user_id, trigger_generation=False)

        # Assert
        assert isinstance(result, SubChapterCreateResponse)
        assert result.sub_chapter_id == UUID(created_sub_chapter["id"])
        assert result.status == SubChapterStatus.DRAFT
        assert result.generation_job_id is None

    @pytest.mark.asyncio
    async def test_create_sub_chapter_with_generation(self, manager, sample_chapter_data):
        """Test sub-chapter creation with content generation triggered."""
        # Arrange
        chapter_id = UUID(sample_chapter_data["id"])
        user_id = uuid4()

        data = SubChapterCreate(
            chapter_id=chapter_id,
            title="Test Sub-Chapter",
            plot_points="Character makes crucial discovery",
            target_word_count=2000
        )

        # Mock chapter lookup
        manager.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_chapter_data]
        )

        # Mock next number
        manager.supabase.rpc.return_value.execute.return_value = MagicMock(data=1)

        # Mock insertion
        created_sub_chapter = {
            "id": str(uuid4()),
            "chapter_id": str(chapter_id),
            "character_id": sample_chapter_data["character_id"],
            "sub_chapter_number": 1,
            "title": data.title,
            "plot_points": data.plot_points
        }

        insert_mock = MagicMock()
        insert_mock.execute.return_value = MagicMock(data=[created_sub_chapter])
        manager.supabase.table.return_value.insert.return_value = insert_mock

        # Mock update for status change
        update_mock = MagicMock()
        update_mock.execute.return_value = MagicMock(data=[created_sub_chapter])
        manager.supabase.table.return_value.update.return_value.eq.return_value = update_mock

        # Mock task queue
        job_id = str(uuid4())
        with patch('api.services.sub_chapter_manager.TaskQueue') as mock_queue:
            mock_queue.enqueue_sub_chapter_generation = AsyncMock(return_value=job_id)

            # Act
            result = await manager.create_sub_chapter(data, user_id, trigger_generation=True)

            # Assert
            assert result.generation_job_id == UUID(job_id)
            assert result.status == SubChapterStatus.IN_PROGRESS
            assert result.websocket_url == f"/ws/generation-jobs/{job_id}"

    @pytest.mark.asyncio
    async def test_create_sub_chapter_chapter_not_found(self, manager):
        """Test creation fails when chapter doesn't exist."""
        # Arrange
        data = SubChapterCreate(
            chapter_id=uuid4(),
            title="Test",
            plot_points="Test"
        )

        # Mock chapter not found
        manager.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not found or access denied"):
            await manager.create_sub_chapter(data, uuid4())

    @pytest.mark.asyncio
    async def test_create_sub_chapter_sequential_numbering(self, manager, sample_chapter_data):
        """Test that sub-chapters are numbered sequentially."""
        # Arrange
        chapter_id = UUID(sample_chapter_data["id"])
        user_id = uuid4()

        data = SubChapterCreate(
            chapter_id=chapter_id,
            title="Third Sub-Chapter",
            plot_points="Third plot"
        )

        # Mock chapter exists
        manager.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_chapter_data]
        )

        # Mock that there are already 2 sub-chapters
        manager.supabase.rpc.return_value.execute.return_value = MagicMock(data=3)

        created_sub_chapter = {
            "id": str(uuid4()),
            "chapter_id": str(chapter_id),
            "character_id": sample_chapter_data["character_id"],
            "sub_chapter_number": 3,  # Should be 3
            "title": data.title,
            "plot_points": data.plot_points
        }

        insert_mock = MagicMock()
        insert_mock.execute.return_value = MagicMock(data=[created_sub_chapter])
        manager.supabase.table.return_value.insert.return_value = insert_mock

        # Act
        result = await manager.create_sub_chapter(data, user_id, trigger_generation=False)

        # Assert
        # Verify RPC was called to get next number
        manager.supabase.rpc.assert_called_once()


class TestSubChapterRetrieval:
    """Tests for sub-chapter retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_sub_chapter_success(self, manager, sample_sub_chapter_data):
        """Test successful retrieval of a single sub-chapter."""
        # Arrange
        sub_chapter_id = UUID(sample_sub_chapter_data["id"])
        user_id = uuid4()

        manager.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_sub_chapter_data]
        )

        # Act
        result = await manager.get_sub_chapter(sub_chapter_id, user_id)

        # Assert
        assert result is not None
        assert isinstance(result, SubChapter)
        assert result.id == sub_chapter_id
        assert result.title == sample_sub_chapter_data["title"]

    @pytest.mark.asyncio
    async def test_get_sub_chapter_not_found(self, manager):
        """Test retrieval when sub-chapter doesn't exist."""
        # Arrange
        manager.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Act
        result = await manager.get_sub_chapter(uuid4(), uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_list_sub_chapters_ordered(self, manager):
        """Test listing sub-chapters returns them in order."""
        # Arrange
        chapter_id = uuid4()
        user_id = uuid4()

        sub_chapters_data = [
            {"id": str(uuid4()), "sub_chapter_number": 1, "title": "First",
             "chapter_id": str(chapter_id), "character_id": str(uuid4()),
             "word_count": 0, "status": "draft",
             "created_at": datetime.utcnow().isoformat(),
             "updated_at": datetime.utcnow().isoformat()},
            {"id": str(uuid4()), "sub_chapter_number": 2, "title": "Second",
             "chapter_id": str(chapter_id), "character_id": str(uuid4()),
             "word_count": 0, "status": "draft",
             "created_at": datetime.utcnow().isoformat(),
             "updated_at": datetime.utcnow().isoformat()},
            {"id": str(uuid4()), "sub_chapter_number": 3, "title": "Third",
             "chapter_id": str(chapter_id), "character_id": str(uuid4()),
             "word_count": 0, "status": "draft",
             "created_at": datetime.utcnow().isoformat(),
             "updated_at": datetime.utcnow().isoformat()},
        ]

        manager.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=sub_chapters_data
        )

        # Act
        result = await manager.list_sub_chapters(chapter_id, user_id)

        # Assert
        assert len(result) == 3
        assert result[0].sub_chapter_number == 1
        assert result[1].sub_chapter_number == 2
        assert result[2].sub_chapter_number == 3


class TestSubChapterUpdate:
    """Tests for sub-chapter update operations."""

    @pytest.mark.asyncio
    async def test_update_sub_chapter_title(self, manager, sample_sub_chapter_data):
        """Test updating sub-chapter title."""
        # Arrange
        sub_chapter_id = UUID(sample_sub_chapter_data["id"])
        user_id = uuid4()

        update_data = SubChapterUpdate(title="Updated Title")

        updated_data = {**sample_sub_chapter_data, "title": "Updated Title"}

        update_mock = MagicMock()
        update_mock.execute.return_value = MagicMock(data=[updated_data])
        manager.supabase.table.return_value.update.return_value.eq.return_value = update_mock

        # Act
        result = await manager.update_sub_chapter(sub_chapter_id, update_data, user_id)

        # Assert
        assert result is not None
        assert result.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_sub_chapter_status(self, manager, sample_sub_chapter_data):
        """Test updating sub-chapter status."""
        # Arrange
        sub_chapter_id = UUID(sample_sub_chapter_data["id"])
        user_id = uuid4()

        update_data = SubChapterUpdate(status=SubChapterStatus.COMPLETED)

        updated_data = {**sample_sub_chapter_data, "status": SubChapterStatus.COMPLETED}

        update_mock = MagicMock()
        update_mock.execute.return_value = MagicMock(data=[updated_data])
        manager.supabase.table.return_value.update.return_value.eq.return_value = update_mock

        # Act
        result = await manager.update_sub_chapter(sub_chapter_id, update_data, user_id)

        # Assert
        assert result.status == SubChapterStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_sub_chapter_not_found(self, manager):
        """Test update fails when sub-chapter doesn't exist."""
        # Arrange
        update_data = SubChapterUpdate(title="New Title")

        update_mock = MagicMock()
        update_mock.execute.return_value = MagicMock(data=[])
        manager.supabase.table.return_value.update.return_value.eq.return_value = update_mock

        # Act
        result = await manager.update_sub_chapter(uuid4(), update_data, uuid4())

        # Assert
        assert result is None


class TestSubChapterDeletion:
    """Tests for sub-chapter deletion."""

    @pytest.mark.asyncio
    async def test_delete_sub_chapter_success(self, manager):
        """Test successful deletion of a sub-chapter."""
        # Arrange
        sub_chapter_id = uuid4()
        user_id = uuid4()

        delete_mock = MagicMock()
        delete_mock.execute.return_value = MagicMock(data=[{"id": str(sub_chapter_id)}])
        manager.supabase.table.return_value.delete.return_value.eq.return_value = delete_mock

        # Act
        result = await manager.delete_sub_chapter(sub_chapter_id, user_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_sub_chapter_not_found(self, manager):
        """Test deletion fails when sub-chapter doesn't exist."""
        # Arrange
        delete_mock = MagicMock()
        delete_mock.execute.return_value = MagicMock(data=[])
        manager.supabase.table.return_value.delete.return_value.eq.return_value = delete_mock

        # Act
        result = await manager.delete_sub_chapter(uuid4(), uuid4())

        # Assert
        assert result is False
