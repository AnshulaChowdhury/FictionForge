"""
Integration tests for Character API endpoints (Epic 2).

These tests verify the full request/response cycle including:
- Request validation
- Authentication
- Database operations
- Response formatting
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from api.main import app


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    user_mock = MagicMock()
    user_mock.id = "550e8400-e29b-41d4-a716-446655440000"
    return user_mock


@pytest.fixture
def auth_headers():
    """Mock authentication headers."""
    return {"Authorization": "Bearer mock-jwt-token"}


class TestCreateCharacterEndpoint:
    """Integration tests for POST /api/characters"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_character_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_trilogy_id,
        sample_character_data,
    ):
        """Test successful character creation via API."""
        # Arrange
        request_data = {
            "trilogy_id": mock_trilogy_id,
            "name": "Dr. Sarah Chen",
            "description": "A brilliant neuroscientist",
            "traits": {
                "personality": ["analytical", "determined"],
                "speech_patterns": ["uses scientific terminology"],
                "physical_description": "Tall with short dark hair",
                "background": "Former MIT neuroscientist",
                "motivations": ["understand consciousness"]
            },
            "character_arc": "Begins as skeptical materialist"
        }

        # Mock Supabase responses
        mock_client = MagicMock()

        # Mock trilogy verification
        trilogy_mock = MagicMock()
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": mock_trilogy_id, "user_id": mock_auth_user.id}
        ]

        # Mock character insert
        characters_mock = MagicMock()
        characters_mock.insert.return_value.execute.return_value.data = [sample_character_data]

        # Mock character select (for updates)
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = [sample_character_data]

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "characters":
                return characters_mock

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.character_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.post(
                            "/api/characters",
                            json=request_data,
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 201
                        data = response.json()
                        assert data["name"] == "Dr. Sarah Chen"
                        assert data["trilogy_id"] == mock_trilogy_id
                        assert "id" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_character_missing_required_field(
        self, mock_auth_user, auth_headers
    ):
        """Test validation error when required field is missing."""
        # Arrange
        request_data = {
            "trilogy_id": "660e8400-e29b-41d4-a716-446655440001",
            # Missing 'name' (required field)
        }

        mock_client = MagicMock()
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.middleware.auth.supabase", mock_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    "/api/characters",
                    json=request_data,
                    headers=auth_headers,
                )

                # Assert
                assert response.status_code == 422  # Validation error


class TestListCharactersEndpoint:
    """Integration tests for GET /api/characters/trilogy/{trilogy_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_characters_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_trilogy_id,
        sample_character_data,
    ):
        """Test listing characters for a trilogy."""
        # Arrange
        mock_client = MagicMock()

        # Mock trilogy verification
        trilogy_mock = MagicMock()
        trilogy_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": mock_trilogy_id, "user_id": mock_auth_user.id}
        ]

        # Mock characters query
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_character_data,
            {**sample_character_data, "id": "different-id", "name": "Another Character"}
        ]

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "characters":
                return characters_mock

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.character_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/characters/trilogy/{mock_trilogy_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["total"] == 2
                        assert len(data["characters"]) == 2


class TestGetCharacterEndpoint:
    """Integration tests for GET /api/characters/{character_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_character_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_character_id,
        sample_character_data,
    ):
        """Test retrieving a single character."""
        # Arrange
        character_with_trilogy = {
            **sample_character_data,
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }

        mock_client = MagicMock()
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = [
            character_with_trilogy
        ]

        mock_client.table.return_value = characters_mock

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.character_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/characters/{mock_character_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["id"] == mock_character_id
                        assert data["name"] == "Dr. Sarah Chen"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_character_not_found(
        self, mock_auth_user, auth_headers
    ):
        """Test 404 when character doesn't exist."""
        # Arrange
        mock_client = MagicMock()
        characters_mock = MagicMock()
        characters_mock.select.return_value.eq.return_value.execute.return_value.data = []

        mock_client.table.return_value = characters_mock

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.character_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            "/api/characters/non-existent-id",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 404


class TestUpdateCharacterEndpoint:
    """Integration tests for PUT /api/characters/{character_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_character_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_character_id,
        sample_character_data,
    ):
        """Test updating a character."""
        # Arrange
        request_data = {
            "name": "Updated Name",
            "description": "Updated description"
        }

        updated_data = {
            **sample_character_data,
            "name": "Updated Name",
            "description": "Updated description"
        }

        character_with_trilogy = {
            **sample_character_data,
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }

        mock_client = MagicMock()
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            character_with_trilogy
        ]

        update_mock = MagicMock()
        update_mock.update.return_value.eq.return_value.execute.return_value.data = [updated_data]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "characters":
                call_count[0] += 1
                return select_mock if call_count[0] == 1 else update_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.character_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.put(
                            f"/api/characters/{mock_character_id}",
                            json=request_data,
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["name"] == "Updated Name"
                        assert data["description"] == "Updated description"


class TestDeleteCharacterEndpoint:
    """Integration tests for DELETE /api/characters/{character_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_character_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_character_id,
        sample_character_data,
    ):
        """Test deleting a character."""
        # Arrange
        character_with_trilogy = {
            **sample_character_data,
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }

        mock_client = MagicMock()
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            character_with_trilogy
        ]

        delete_mock = MagicMock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value.data = [sample_character_data]

        call_count = [0]
        def table_side_effect(table_name):
            if table_name == "characters":
                call_count[0] += 1
                return select_mock if call_count[0] == 1 else delete_mock
            return MagicMock()

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.character_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.delete(
                            f"/api/characters/{mock_character_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["id"] == mock_character_id
                        assert "deleted successfully" in data["message"]
