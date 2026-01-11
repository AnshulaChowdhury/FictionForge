"""
Integration tests for Chapter API endpoints (Epic 4).

These tests verify the full request/response cycle including:
- Request validation
- Authentication
- Database operations
- Response formatting
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from datetime import datetime
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


class TestCreateChapterEndpoint:
    """Integration tests for POST /api/chapters"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_chapter_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_book_ids,
        mock_character_id,
        sample_chapter_data,
    ):
        """Test successful chapter creation via API."""
        # Arrange
        request_data = {
            "book_id": mock_book_ids[0],
            "character_id": mock_character_id,
            "title": "The Awakening",
            "description": "Sarah discovers the quantum consciousness lab",
            "target_word_count": 3000,
        }

        # Mock Supabase responses
        mock_client = MagicMock()

        # Mock book ownership verification
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }]

        # Mock character verification
        book_response_data = [{"trilogy_id": "660e8400-e29b-41d4-a716-446655440001"}]
        char_response_data = [{
            "id": mock_character_id,
            "trilogy_id": "660e8400-e29b-41d4-a716-446655440001"
        }]

        # Mock next chapter number query
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

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.post(
                            "/api/chapters",
                            json=request_data,
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 201
                        data = response.json()
                        assert data["title"] == "The Awakening"
                        assert data["chapter_number"] == 1
                        assert data["target_word_count"] == 3000

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_chapter_invalid_book_id(
        self,
        mock_auth_user,
        auth_headers,
        mock_character_id,
    ):
        """Test chapter creation with invalid book ID."""
        # Arrange
        request_data = {
            "book_id": "invalid-uuid",
            "character_id": mock_character_id,
            "title": "Test Chapter",
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
                        "/api/chapters",
                        json=request_data,
                        headers=auth_headers,
                    )

                    # Assert
                    assert response.status_code == 422


class TestListChaptersEndpoint:
    """Integration tests for GET /api/chapters/book/{book_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_chapters_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_book_ids,
        sample_chapter_data,
    ):
        """Test listing all chapters for a book."""
        # Arrange
        mock_client = MagicMock()

        # Mock book ownership
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }]

        # Mock chapters query
        chapters_mock = MagicMock()
        chapters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_chapter_data
        ]

        def table_side_effect(table_name):
            if table_name == "books":
                return book_mock
            elif table_name == "chapters":
                return chapters_mock

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/chapters/book/{mock_book_ids[0]}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["total"] == 1
                        assert len(data["chapters"]) == 1
                        assert data["chapters"][0]["title"] == "The Awakening"


class TestGetChapterEndpoint:
    """Integration tests for GET /api/chapters/{chapter_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_chapter_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_chapter_id,
        sample_chapter_data,
    ):
        """Test retrieving a single chapter."""
        # Arrange
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_auth_user.id}
            }
        }

        mock_client = MagicMock()
        chapters_mock = MagicMock()
        chapters_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        mock_client.table.return_value = chapters_mock

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/chapters/{mock_chapter_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["id"] == mock_chapter_id
                        assert data["title"] == "The Awakening"


class TestUpdateChapterEndpoint:
    """Integration tests for PUT /api/chapters/{chapter_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_chapter_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_chapter_id,
        sample_chapter_data,
    ):
        """Test updating a chapter."""
        # Arrange
        request_data = {
            "title": "Updated Title",
            "description": "Updated description"
        }

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
                "trilogy_projects": {"user_id": mock_auth_user.id}
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

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.put(
                            f"/api/chapters/{mock_chapter_id}",
                            json=request_data,
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["title"] == "Updated Title"
                        assert data["description"] == "Updated description"


class TestDeleteChapterEndpoint:
    """Integration tests for DELETE /api/chapters/{chapter_id}"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_chapter_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_chapter_id,
        sample_chapter_data,
    ):
        """Test deleting a chapter."""
        # Arrange
        mock_client = MagicMock()

        # Mock get_chapter
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_auth_user.id}
            }
        }
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        # Mock delete
        delete_mock = MagicMock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value.data = [sample_chapter_data]

        # Mock renumbering query
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

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.delete(
                            f"/api/chapters/{mock_chapter_id}",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["id"] == mock_chapter_id
                        assert "deleted successfully" in data["message"]


class TestReorderChapterEndpoint:
    """Integration tests for POST /api/chapters/{chapter_id}/reorder"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_reorder_chapter_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_book_ids,
    ):
        """Test reordering a chapter."""
        # Arrange
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

        request_data = {"new_position": 3}

        mock_client = MagicMock()

        # Mock get_chapter
        chapter_with_book = {
            **chapters_data[0],
            "books": {
                "trilogy_projects": {"user_id": mock_auth_user.id}
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
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }]

        # Mock get_book_chapters
        chapters_list_mock = MagicMock()
        chapters_list_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = chapters_data

        # Mock updates
        update_mock = MagicMock()
        update_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        # Mock final get_book_chapters
        final_chapters_mock = MagicMock()
        final_chapters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = chapters_data

        call_count = {"chapters": 0}
        def table_side_effect(table_name):
            if table_name == "books":
                return book_mock
            elif table_name == "chapters":
                call_count["chapters"] += 1
                if call_count["chapters"] == 1:
                    return get_chapter_mock
                elif call_count["chapters"] == 2:
                    return chapters_list_mock
                elif call_count["chapters"] >= 3 and call_count["chapters"] <= 5:
                    return update_mock
                else:
                    return final_chapters_mock

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.post(
                            "/api/chapters/ch1/reorder",
                            json=request_data,
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["total"] == 3


class TestChapterProgressEndpoint:
    """Integration tests for GET /api/chapters/{chapter_id}/progress"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_chapter_progress_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_chapter_id,
        sample_chapter_data,
    ):
        """Test getting chapter progress."""
        # Arrange
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_auth_user.id}
            }
        }

        mock_client = MagicMock()
        chapters_mock = MagicMock()
        chapters_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        mock_client.table.return_value = chapters_mock

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/chapters/{mock_chapter_id}/progress",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["chapter_id"] == mock_chapter_id
                        assert "percentage" in data
                        assert "status" in data


class TestBookProgressEndpoint:
    """Integration tests for GET /api/chapters/book/{book_id}/progress"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_book_progress_success(
        self,
        mock_auth_user,
        auth_headers,
        mock_book_ids,
        sample_chapter_data,
    ):
        """Test getting book progress."""
        # Arrange
        mock_client = MagicMock()

        # Mock book ownership
        book_mock = MagicMock()
        book_mock.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": mock_book_ids[0],
            "trilogy_projects": {"user_id": mock_auth_user.id}
        }]

        # Mock chapters query
        chapters_mock = MagicMock()
        chapters_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_chapter_data
        ]

        # Mock get_chapter call for progress calculation
        chapter_with_book = {
            **sample_chapter_data,
            "books": {
                "trilogy_projects": {"user_id": mock_auth_user.id}
            }
        }
        get_chapter_mock = MagicMock()
        get_chapter_mock.select.return_value.eq.return_value.execute.return_value.data = [
            chapter_with_book
        ]

        call_count = {"chapters": 0}
        def table_side_effect(table_name):
            if table_name == "books":
                return book_mock
            elif table_name == "chapters":
                call_count["chapters"] += 1
                # First call: get_book_chapters, second call: get_chapter for progress
                return chapters_mock if call_count["chapters"] == 1 else get_chapter_mock

        mock_client.table.side_effect = table_side_effect

        # Mock auth
        auth_response = MagicMock()
        auth_response.user = mock_auth_user
        mock_client.auth.get_user.return_value = auth_response

        with patch("api.utils.supabase_client.create_client", return_value=mock_client):
            with patch("api.middleware.auth.supabase", mock_client):
                with patch("api.services.chapter_manager.supabase", mock_client):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Act
                        response = await client.get(
                            f"/api/chapters/book/{mock_book_ids[0]}/progress",
                            headers=auth_headers,
                        )

                        # Assert
                        assert response.status_code == 200
                        data = response.json()
                        assert data["book_id"] == mock_book_ids[0]
                        assert "total_chapters" in data
                        assert "overall_percentage" in data
                        assert "chapters_by_status" in data
