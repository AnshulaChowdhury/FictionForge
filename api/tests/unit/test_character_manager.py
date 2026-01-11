"""
Unit tests for CharacterManager service (Epic 2).

Tests cover:
- Successful character creation
- Get operations (single and list)
- Update operations
- Delete operations
- Error handling and validation
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from api.services.character_manager import (
    CharacterManager,
    CharacterCreationError,
    CharacterNotFoundError,
    CharacterUpdateError,
    CharacterDeletionError,
)
from api.models.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterTraits,
)
from postgrest.exceptions import APIError


class TestCharacterManagerCreate:
    """Tests for CharacterManager.create_character()"""

    @pytest.mark.asyncio
    async def test_create_character_success(
        self, mock_user_id, mock_trilogy_id, sample_character_data
    ):
        """Test successful character creation."""
        # Arrange
        traits = CharacterTraits(
            personality=["analytical", "determined", "empathetic"],
            speech_patterns=["uses scientific terminology", "speaks precisely"],
            physical_description="Tall with short dark hair and piercing blue eyes",
            background="Former MIT neuroscientist",
            motivations=["understand consciousness", "prevent AI suffering"]
        )

        request = CharacterCreate(
            trilogy_id=mock_trilogy_id,
            name="Dr. Sarah Chen",
            description="A brilliant neuroscientist",
            traits=traits,
            character_arc="Begins as skeptical materialist",
        )

        # Mock Supabase
        mock_client = MagicMock()

        # Mock trilogy verification
        trilogy_mock = MagicMock()
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": mock_trilogy_id, "user_id": mock_user_id}
        ]

        # Mock character insert
        characters_mock = MagicMock()
        characters_mock.insert.return_value.execute.return_value.data = [sample_character_data]

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "characters":
                return characters_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act
            response = await manager.create_character(request)

            # Assert
            assert isinstance(response, CharacterResponse)
            assert response.name == "Dr. Sarah Chen"
            assert response.trilogy_id == mock_trilogy_id
            assert response.traits is not None
            assert isinstance(response.traits, CharacterTraits)

    @pytest.mark.asyncio
    async def test_create_character_minimal_fields(
        self, mock_user_id, mock_trilogy_id, mock_character_id
    ):
        """Test character creation with only required fields."""
        # Arrange
        request = CharacterCreate(
            trilogy_id=mock_trilogy_id,
            name="John Doe",
        )

        minimal_character_data = {
            "id": mock_character_id,
            "trilogy_id": mock_trilogy_id,
            "name": "John Doe",
            "description": None,
            "traits": None,
            "character_arc": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        mock_client = MagicMock()

        trilogy_mock = MagicMock()
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": mock_trilogy_id, "user_id": mock_user_id}
        ]

        characters_mock = MagicMock()
        characters_mock.insert.return_value.execute.return_value.data = [minimal_character_data]

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "characters":
                return characters_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act
            response = await manager.create_character(request)

            # Assert
            assert response.name == "John Doe"
            assert response.description is None
            assert response.traits is None
            assert response.character_arc is None

    @pytest.mark.asyncio
    async def test_create_character_trilogy_not_found(
        self, mock_user_id, mock_trilogy_id
    ):
        """Test error when trilogy doesn't exist."""
        # Arrange
        request = CharacterCreate(
            trilogy_id=mock_trilogy_id,
            name="Test Character",
        )

        mock_client = MagicMock()
        trilogy_mock = MagicMock()
        # No trilogy data returned
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = []

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(CharacterCreationError, match="Failed to create character"):
                await manager.create_character(request)


class TestCharacterManagerGet:
    """Tests for CharacterManager get operations"""

    @pytest.mark.asyncio
    async def test_get_trilogy_characters_success(
        self, mock_user_id, mock_trilogy_id, sample_character_data
    ):
        """Test retrieving all characters for a trilogy."""
        # Arrange
        mock_client = MagicMock()

        # Mock trilogy verification
        trilogy_mock = MagicMock()
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": mock_trilogy_id, "user_id": mock_user_id}
        ]

        # Mock characters query
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_character_data
        ]

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "characters":
                return characters_mock

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act
            response = await manager.get_trilogy_characters(mock_trilogy_id)

            # Assert
            assert response.total == 1
            assert len(response.characters) == 1
            assert response.characters[0].name == "Dr. Sarah Chen"

    @pytest.mark.asyncio
    async def test_get_character_success(
        self, mock_user_id, mock_character_id, sample_character_data
    ):
        """Test retrieving a single character."""
        # Arrange
        character_with_trilogy = {
            **sample_character_data,
            "trilogy_projects": {"user_id": mock_user_id}
        }

        mock_client = MagicMock()
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = [
            character_with_trilogy
        ]

        mock_client.table.return_value = characters_mock

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act
            response = await manager.get_character(mock_character_id)

            # Assert
            assert response.id == mock_character_id
            assert response.name == "Dr. Sarah Chen"
            assert "trilogy_projects" not in response.model_dump()

    @pytest.mark.asyncio
    async def test_get_character_not_found(self, mock_user_id):
        """Test error when character doesn't exist."""
        # Arrange
        mock_client = MagicMock()
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = []

        mock_client.table.return_value = characters_mock

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(CharacterNotFoundError):
                await manager.get_character("non-existent-id")


class TestCharacterManagerUpdate:
    """Tests for CharacterManager.update_character()"""

    @pytest.mark.asyncio
    async def test_update_character_success(
        self, mock_user_id, mock_character_id, sample_character_data
    ):
        """Test successful character update."""
        # Arrange
        request = CharacterUpdate(
            name="Updated Name",
            description="Updated description"
        )

        updated_data = {
            **sample_character_data,
            "name": "Updated Name",
            "description": "Updated description"
        }

        mock_client = MagicMock()

        # Mock get_character (verification)
        character_with_trilogy = {
            **sample_character_data,
            "trilogy_projects": {"user_id": mock_user_id}
        }
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            character_with_trilogy
        ]

        # Mock update
        update_mock = MagicMock()
        update_mock.update.return_value.eq.return_value.execute.return_value.data = [updated_data]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "characters":
                call_count[0] += 1
                # First call is for get_character, second is for update
                return select_mock if call_count[0] == 1 else update_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act
            response = await manager.update_character(mock_character_id, request)

            # Assert
            assert response.name == "Updated Name"
            assert response.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_character_not_found(self, mock_user_id):
        """Test error when updating non-existent character."""
        # Arrange
        request = CharacterUpdate(name="New Name")

        mock_client = MagicMock()
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = []

        mock_client.table.return_value = characters_mock

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(CharacterNotFoundError):
                await manager.update_character("non-existent-id", request)


class TestCharacterManagerDelete:
    """Tests for CharacterManager.delete_character()"""

    @pytest.mark.asyncio
    async def test_delete_character_success(
        self, mock_user_id, mock_character_id, sample_character_data
    ):
        """Test successful character deletion."""
        # Arrange
        mock_client = MagicMock()

        # Mock get_character (verification)
        character_with_trilogy = {
            **sample_character_data,
            "trilogy_projects": {"user_id": mock_user_id}
        }
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            character_with_trilogy
        ]

        # Mock delete
        delete_mock = MagicMock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value.data = [sample_character_data]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "characters":
                call_count[0] += 1
                # First call is for get_character, second is for delete
                return select_mock if call_count[0] == 1 else delete_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act
            response = await manager.delete_character(mock_character_id)

            # Assert
            assert response.id == mock_character_id
            assert "deleted successfully" in response.message

    @pytest.mark.asyncio
    async def test_delete_character_not_found(self, mock_user_id):
        """Test error when deleting non-existent character."""
        # Arrange
        mock_client = MagicMock()
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = []

        mock_client.table.return_value = characters_mock

        with patch("api.services.character_manager.supabase", mock_client):
            manager = CharacterManager(user_id=mock_user_id)

            # Act & Assert
            with pytest.raises(CharacterNotFoundError):
                await manager.delete_character("non-existent-id")
