"""
Integration tests for Trilogy API endpoints (Epic 1).

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


class TestCreateTrilogyEndpoint:
    """Integration tests for POST /api/trilogy/create"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_trilogy_success(
        self,
        mock_auth_user,
        auth_headers,
        sample_trilogy_data,
        sample_books_data,
    ):
        """Test successful trilogy creation via API."""
        # Arrange
        request_data = {
            "title": "The Consciousness Trilogy",
            "description": "A sci-fi trilogy about consciousness.",
            "author": "Jane Doe",
            "narrative_overview": "Humanity's journey through evolving consciousness.",
        }

        # Mock Supabase responses
        mock_client = MagicMock()
        trilogy_mock = MagicMock()
        trilogy_mock.insert.return_value.execute.return_value.data = [sample_trilogy_data]

        books_mock = MagicMock()
        books_mock.insert.return_value.execute.return_value.data = sample_books_data

        def table_side_effect(table_name):
            if table_name == "trilogy_projects":
                return trilogy_mock
            elif table_name == "books":
                return books_mock

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.trilogy_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.post(
                            "/api/trilogy/create",
                            json=request_data,
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 201
                        data = response.json()
                        assert data["trilogy"]["title"] == "The Consciousness Trilogy"
                        assert len(data["books"]) == 3
                        assert data["message"] == "Project created successfully!"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_trilogy_missing_required_field(self, mock_auth_user, auth_headers):
        """Test validation error when required field is missing."""
        # Arrange
        request_data = {
            "description": "A trilogy without a title",
            # Missing 'title' and 'author' (required fields)
        }

        mock_client = MagicMock()
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Act
                    response = await client.post(
                        "/api/trilogy/create",
                        json=request_data,
                        headers=auth_headers,
                    )

                    # Assert
                    assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_trilogy_title_too_long(self, mock_auth_user, auth_headers):
        """Test validation error when title exceeds max length."""
        # Arrange
        request_data = {
            "title": "A" * 101,  # 101 characters (max is 100)
            "author": "Test Author",
        }

        mock_client = MagicMock()
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Act
                    response = await client.post(
                        "/api/trilogy/create",
                        json=request_data,
                        headers=auth_headers,
                    )

                    # Assert
                    assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_trilogy_unauthorized(self):
        """Test that endpoint requires authentication."""
        # Arrange
        request_data = {
            "title": "Test Trilogy",
            "author": "Test Author",
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Act - no auth headers
            response = await client.post(
                "/api/trilogy/create",
                json=request_data,
            )

            # Assert
            assert response.status_code == 403  # No auth credentials


class TestListTrilogiesEndpoint:
    """Integration tests for GET /api/trilogy"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_trilogies_success(
        self, mock_auth_user, auth_headers, sample_trilogy_data
    ):
        """Test retrieving user's trilogies."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [sample_trilogy_data]

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.trilogy_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            "/api/trilogy",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert len(data) == 1
                        assert data[0]["title"] == "The Consciousness Trilogy"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_trilogies_empty(self, mock_auth_user, auth_headers):
        """Test retrieving trilogies when user has none."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.trilogy_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            "/api/trilogy",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data == []


class TestGetTrilogyEndpoint:
    """Integration tests for GET /api/trilogy/{trilogy_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_trilogy_success(
        self, mock_auth_user, auth_headers, sample_trilogy_data, mock_trilogy_id
    ):
        """Test retrieving a specific trilogy."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [sample_trilogy_data]

        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.trilogy_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/trilogy/{mock_trilogy_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["id"] == mock_trilogy_id
                        assert data["title"] == "The Consciousness Trilogy"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_trilogy_not_found(
        self, mock_auth_user, auth_headers, mock_trilogy_id
    ):
        """Test 404 when trilogy doesn't exist."""
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.trilogy_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/trilogy/{mock_trilogy_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 404
