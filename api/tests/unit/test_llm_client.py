"""
Unit tests for LLMClient (Epic 5A).

Tests cover:
- LLM content generation via AWS Bedrock
- API Gateway integration
- Error handling and retries
- Response parsing
- Token limits and temperature settings
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from api.services.llm_client import LLMClient, LLMError, get_llm_client


class TestLLMClient:
    """Tests for LLMClient"""

    @pytest.fixture
    def client(self):
        """Create LLMClient instance."""
        with patch.dict('os.environ', {
            'AWS_API_GATEWAY_URL': 'https://test-api.execute-api.us-east-1.amazonaws.com/prod/generate',
            'AWS_BEDROCK_TIMEOUT': '300'
        }):
            return LLMClient()

    @pytest.fixture
    def mock_httpx_response(self):
        """Mock httpx response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "generated_text": "This is the generated content from the LLM.",
            "model_id": "mistral.mistral-7b-instruct-v0:2",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 250,
                "total_tokens": 400
            }
        }
        return mock_response

    @pytest.mark.asyncio
    async def test_generate_success(self, client, mock_httpx_response):
        """Test successful content generation."""
        # Arrange
        prompt = "Write a story about a scientist discovering consciousness transfer."

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_httpx_response)

        # Act
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            result = await client.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7
            )

        # Assert
        assert result == "This is the generated content from the LLM."
        mock_http_client.post.assert_called_once()

        # Verify request payload
        call_args = mock_http_client.post.call_args
        payload = call_args[1]['json']
        assert payload['prompt'] == prompt
        assert payload['max_tokens'] == 2000
        assert payload['temperature'] == 0.7
        assert payload['model_id'] == "mistral.mistral-7b-instruct-v0:2"

    @pytest.mark.asyncio
    async def test_generate_with_default_params(self, client, mock_httpx_response):
        """Test generation with default parameters."""
        # Arrange
        prompt = "Test prompt"

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_httpx_response)

        # Act
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            result = await client.generate(prompt=prompt)

        # Assert
        assert result is not None

        # Verify default parameters were used
        call_args = mock_http_client.post.call_args
        payload = call_args[1]['json']
        assert payload['max_tokens'] == 4000
        assert payload['temperature'] == 0.7
        assert payload['top_p'] == 0.9

    @pytest.mark.asyncio
    async def test_generate_api_error(self, client):
        """Test handling of API errors."""
        # Arrange
        prompt = "Test prompt"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # Act & Assert
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            with pytest.raises(LLMError, match="HTTP error"):
                await client.generate(prompt=prompt)

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, client):
        """Test handling of timeout errors."""
        # Arrange
        prompt = "Test prompt"

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        # Act & Assert
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            with pytest.raises(LLMError, match="Request timed out"):
                await client.generate(prompt=prompt)

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, client):
        """Test handling of connection errors."""
        # Arrange
        prompt = "Test prompt"

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        # Act & Assert
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            with pytest.raises(LLMError, match="Connection failed"):
                await client.generate(prompt=prompt)

    @pytest.mark.asyncio
    async def test_generate_malformed_response(self, client):
        """Test handling of malformed JSON response."""
        # Arrange
        prompt = "Test prompt"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # Act & Assert
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            with pytest.raises(LLMError, match="Invalid JSON"):
                await client.generate(prompt=prompt)

    @pytest.mark.asyncio
    async def test_generate_missing_generated_text(self, client):
        """Test handling when generated_text is missing from response."""
        # Arrange
        prompt = "Test prompt"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model_id": "mistral.mistral-7b-instruct-v0:2",
            # missing "generated_text" key
        }

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # Act & Assert
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            with pytest.raises(LLMError, match="generated_text"):
                await client.generate(prompt=prompt)

    @pytest.mark.asyncio
    async def test_generate_various_temperatures(self, client, mock_httpx_response):
        """Test generation with various temperature settings."""
        temperatures = [0.0, 0.5, 1.0, 1.5]

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_httpx_response)

        for temp in temperatures:
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_http_client

                # Act
                result = await client.generate(
                    prompt="Test",
                    temperature=temp
                )

                # Assert
                assert result is not None
                call_args = mock_http_client.post.call_args
                assert call_args[1]['json']['temperature'] == temp

    @pytest.mark.asyncio
    async def test_generate_various_token_limits(self, client, mock_httpx_response):
        """Test generation with various max_token settings."""
        token_limits = [500, 1000, 2000, 4000]

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_httpx_response)

        for limit in token_limits:
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_http_client

                # Act
                result = await client.generate(
                    prompt="Test",
                    max_tokens=limit
                )

                # Assert
                assert result is not None
                call_args = mock_http_client.post.call_args
                assert call_args[1]['json']['max_tokens'] == limit

    @pytest.mark.asyncio
    async def test_generate_empty_prompt(self, client):
        """Test that empty prompt is handled."""
        # Act & Assert
        # The client should still send the request, but it might get an error from the API
        with pytest.raises(Exception):
            await client.generate(prompt="")

    @pytest.mark.asyncio
    async def test_generate_very_long_prompt(self, client, mock_httpx_response):
        """Test generation with a very long prompt."""
        # Arrange
        long_prompt = "This is a sentence. " * 1000  # Very long prompt

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_httpx_response)

        # Act
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            result = await client.generate(prompt=long_prompt)

        # Assert
        assert result is not None

    def test_get_llm_client(self):
        """Test get_llm_client singleton function."""
        with patch.dict('os.environ', {
            'AWS_API_GATEWAY_URL': 'https://test-api.execute-api.us-east-1.amazonaws.com/prod/generate',
            'AWS_BEDROCK_TIMEOUT': '300'
        }):
            # Act
            client1 = get_llm_client()
            client2 = get_llm_client()

            # Assert
            assert client1 is client2  # Same instance (singleton)
            assert isinstance(client1, LLMClient)

    @pytest.mark.asyncio
    async def test_custom_top_p(self, client, mock_httpx_response):
        """Test generation with custom top_p parameter."""
        # Arrange
        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_httpx_response)

        # Act
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            result = await client.generate(
                prompt="Test",
                top_p=0.95
            )

        # Assert
        assert result is not None
        call_args = mock_http_client.post.call_args
        assert call_args[1]['json']['top_p'] == 0.95

    @pytest.mark.asyncio
    async def test_api_url_configuration(self):
        """Test that API URL is correctly configured from settings."""
        with patch.dict('os.environ', {
            'AWS_API_GATEWAY_URL': 'https://custom-url.amazonaws.com/test',
            'AWS_BEDROCK_TIMEOUT': '300'
        }):
            client = LLMClient()
            assert client.api_url == 'https://custom-url.amazonaws.com/test'

    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """Test that timeout is correctly configured from settings."""
        with patch.dict('os.environ', {
            'AWS_API_GATEWAY_URL': 'https://test-api.execute-api.us-east-1.amazonaws.com/prod/generate',
            'AWS_BEDROCK_TIMEOUT': '600'
        }):
            client = LLMClient()
            assert client.timeout == 600


class TestLLMClientEdgeCases:
    """Edge case tests for LLMClient"""

    @pytest.mark.asyncio
    async def test_unicode_in_prompt(self):
        """Test handling of unicode characters in prompt."""
        with patch.dict('os.environ', {
            'AWS_API_GATEWAY_URL': 'https://test-api.execute-api.us-east-1.amazonaws.com/prod/generate',
            'AWS_BEDROCK_TIMEOUT': '300'
        }):
            client = LLMClient()

            prompt = "Write about consciousness: 意識 🧠 ψυχή"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "generated_text": "Response with unicode: 回答",
            }

            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_http_client

                result = await client.generate(prompt=prompt)

                assert "unicode" in result.lower()

    @pytest.mark.asyncio
    async def test_special_characters_in_prompt(self):
        """Test handling of special characters in prompt."""
        with patch.dict('os.environ', {
            'AWS_API_GATEWAY_URL': 'https://test-api.execute-api.us-east-1.amazonaws.com/prod/generate',
            'AWS_BEDROCK_TIMEOUT': '300'
        }):
            client = LLMClient()

            prompt = "Write about: \n\t\"consciousness\" & 'AI' <testing> $special% #chars!"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "generated_text": "Generated text",
            }

            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_http_client

                result = await client.generate(prompt=prompt)

                assert result is not None
