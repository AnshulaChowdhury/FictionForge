"""
Unit tests for TrilogyManager service (Epic 1).

Tests cover:
- Successful trilogy creation with 3 books
- Validation of input data
- Error handling and rollback
- Get operations
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from api.services.trilogy_manager import TrilogyManager, TrilogyCreationError
from api.models.trilogy import CreateTrilogyRequest, CreateTrilogyResponse
from postgrest.exceptions import APIError


class TestTrilogyManagerCreate:
    """Tests for TrilogyManager.create_project()"""

    @pytest.mark.asyncio
    async def test_create_project_success(
        self, mock_user_id, mock_supabase_client, sample_trilogy_data, sample_books_data
    ):
        """Test successful trilogy creation with 3 auto-generated books."""
        # Arrange
        request = CreateTrilogyRequest(
            title="The Consciousness Trilogy",
            description="A sci-fi trilogy about consciousness.",
            author="Jane Doe",
            narrative_overview="Humanity's journey through evolving consciousness.",
        )

        with patch("api.services.trilogy_manager.supabase", mock_supabase_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act
            response = await manager.create_project(request)

            # Assert
            assert isinstance(response, CreateTrilogyResponse)
            assert response.trilogy.title == "The Consciousness Trilogy"
            assert response.trilogy.author == "Jane Doe"
            assert len(response.books) == 3
            assert response.books[0].book_number == 1
            assert response.books[1].book_number == 2
            assert response.books[2].book_number == 3
            assert response.message == "Project created successfully!"

    @pytest.mark.asyncio
    async def test_create_project_with_minimal_fields(
        self, mock_user_id, mock_trilogy_id, sample_books_data
    ):
        """Test trilogy creation with only required fields (title and author)."""
        # Arrange
        request = CreateTrilogyRequest(
            title="Minimal Trilogy",
            author="John Smith",
        )

        minimal_trilogy_data = {
            "id": mock_trilogy_id,
            "user_id": mock_user_id,
            "title": "Minimal Trilogy",
            "description": None,
            "author": "John Smith",
            "narrative_overview": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        mock_client = MagicMock()
        trilogy_mock = MagicMock()
        trilogy_mock.insert.return_value.execute.return_value.data = [
            minimal_trilogy_data
        ]

        books_mock = MagicMock()
        books_mock.insert.return_value.execute.return_value.data = sample_books_data

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "books":
                return books_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act
            response = await manager.create_project(request)

            # Assert
            assert response.trilogy.title == "Minimal Trilogy"
            assert response.trilogy.author == "John Smith"
            assert response.trilogy.description is None
            assert response.trilogy.narrative_overview is None

    @pytest.mark.asyncio
    async def test_create_project_trilogy_insert_fails(self, mock_user_id):
        """Test error handling when trilogy insert fails."""
        # Arrange
        request = CreateTrilogyRequest(
            title="Test Trilogy",
            author="Test Author",
        )

        mock_client = MagicMock()
        trilogy_mock = MagicMock()
        trilogy_mock.insert.return_value.execute.return_value.data = []  # Empty response

        mock_client.table.return_value = trilogy_mock

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(TrilogyCreationError) as exc_info:
                await manager.create_project(request)

            assert "Failed to create trilogy" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_books_insert_fails(
        self, mock_user_id, sample_trilogy_data
    ):
        """Test rollback when book creation fails."""
        # Arrange
        request = CreateTrilogyRequest(
            title="Test Trilogy",
            author="Test Author",
        )

        mock_client = MagicMock()

        # Trilogy insert succeeds
        trilogy_mock = MagicMock()
        trilogy_mock.insert.return_value.execute.return_value.data = [sample_trilogy_data]

        # Books insert fails (returns only 2 books instead of 3)
        books_mock = MagicMock()
        books_mock.insert.return_value.execute.return_value.data = [
            {"id": "book-1", "book_number": 1},
            {"id": "book-2", "book_number": 2},
        ]

        # Mock delete for rollback
        delete_mock = MagicMock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value = None

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                # Return different mocks for insert vs delete
                if hasattr(table_side_effect, 'call_count'):
                    table_side_effect.call_count += 1
                else:
                    table_side_effect.call_count = 1

                if table_side_effect.call_count == 1:
                    return trilogy_mock
                else:
                    return delete_mock
            elif table_name == "books":
                return books_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(TrilogyCreationError) as exc_info:
                await manager.create_project(request)

            assert "Failed to create all 3 books" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_database_error(self, mock_user_id):
        """Test error handling when database operation raises APIError."""
        # Arrange
        request = CreateTrilogyRequest(
            title="Test Trilogy",
            author="Test Author",
        )

        mock_client = MagicMock()
        trilogy_mock = MagicMock()
        # APIError expects a dict with 'message', 'code', etc.
        trilogy_mock.insert.return_value.execute.side_effect = APIError(
            {"message": "Database error", "code": "500"}
        )

        mock_client.table.return_value = trilogy_mock

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(TrilogyCreationError) as exc_info:
                await manager.create_project(request)

            assert "Database error during trilogy creation" in str(exc_info.value)


class TestTrilogyManagerGet:
    """Tests for TrilogyManager get operations"""

    @pytest.mark.asyncio
    async def test_get_user_trilogies_success(
        self, mock_user_id, sample_trilogy_data
    ):
        """Test retrieving all user's trilogies."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [sample_trilogy_data]

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act
            trilogies = await manager.get_user_trilogies()

            # Assert
            assert len(trilogies) == 1
            assert trilogies[0].title == "The Consciousness Trilogy"

    @pytest.mark.asyncio
    async def test_get_user_trilogies_empty(self, mock_user_id):
        """Test retrieving trilogies when user has none."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act
            trilogies = await manager.get_user_trilogies()

            # Assert
            assert trilogies == []

    @pytest.mark.asyncio
    async def test_get_trilogy_by_id_success(
        self, mock_user_id, mock_trilogy_id, sample_trilogy_data
    ):
        """Test retrieving a specific trilogy by ID."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [sample_trilogy_data]

        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act
            trilogy = await manager.get_trilogy_by_id(mock_trilogy_id)

            # Assert
            assert trilogy is not None
            assert trilogy.id == mock_trilogy_id
            assert trilogy.title == "The Consciousness Trilogy"

    @pytest.mark.asyncio
    async def test_get_trilogy_by_id_not_found(self, mock_user_id, mock_trilogy_id):
        """Test retrieving a trilogy that doesn't exist."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act
            trilogy = await manager.get_trilogy_by_id(mock_trilogy_id)

            # Assert
            assert trilogy is None


class TestTrilogyManagerRollback:
    """Tests for rollback functionality"""

    @pytest.mark.asyncio
    async def test_rollback_trilogy_success(self, mock_user_id, mock_trilogy_id):
        """Test successful rollback of a trilogy."""
        # Arrange
        mock_client = MagicMock()
        delete_mock = MagicMock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value = None

        mock_client.table.return_value = delete_mock

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act (should not raise)
            await manager._rollback_trilogy(mock_trilogy_id)

            # Assert - verify delete was called
            mock_client.table.assert_called_with("trilogy_projects")

    @pytest.mark.asyncio
    async def test_rollback_trilogy_none(self, mock_user_id):
        """Test rollback when trilogy_id is None (nothing to rollback)."""
        # Arrange
        mock_client = MagicMock()

        with patch("api.services.trilogy_manager.supabase", mock_client):
            manager = TrilogyManager(user_id=mock_user_id)

            # Act (should not raise and should not call delete)
            await manager._rollback_trilogy(None)

            # Assert - verify delete was NOT called
            mock_client.table.assert_not_called()
