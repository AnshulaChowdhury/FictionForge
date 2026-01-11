"""
LLM Client for Epic 5A

Handles interaction with AWS Bedrock (Mistral 7B) via Lambda + API Gateway
for content generation with character-specific RAG.
"""

import logging
import httpx
from typing import Dict, Any, Optional
from api.config import get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM generation fails"""
    pass


class LLMClient:
    """Client for AWS Bedrock Mistral 7B via Lambda"""

    def __init__(self):
        self.settings = get_settings()
        self.api_url = self.settings.aws_api_gateway_url
        self.timeout = self.settings.aws_bedrock_timeout
        self.model_id = "mistral.mistral-7b-instruct-v0:2"

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Generate content using AWS Bedrock Mistral 7B.

        Args:
            prompt: The enhanced prompt with character context
            max_tokens: Maximum tokens to generate (default 4000 ~ 3000 words)
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter

        Returns:
            Generated text content

        Raises:
            LLMError: If generation fails
        """
        try:
            logger.info(
                f"Generating content with Mistral 7B "
                f"(max_tokens={max_tokens}, temperature={temperature})"
            )

            # Prepare request payload for Lambda
            payload = {
                "model_id": self.model_id,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }

            # Call AWS API Gateway -> Lambda -> Bedrock
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload
                )

                response.raise_for_status()

                result = response.json()

                # Extract generated text from response
                # Handle various response formats from AWS Bedrock
                generated_text = None

                if "outputs" in result and isinstance(result["outputs"], list) and len(result["outputs"]) > 0:
                    # Bedrock format: {"outputs": [{"text": "...", "stop_reason": "stop"}]}
                    generated_text = result["outputs"][0].get("text", "")
                elif "body" in result:
                    # Lambda returns JSON with body field
                    import json
                    body = json.loads(result["body"]) if isinstance(result["body"], str) else result["body"]
                    if "outputs" in body and isinstance(body["outputs"], list) and len(body["outputs"]) > 0:
                        generated_text = body["outputs"][0].get("text", "")
                    else:
                        generated_text = body.get("generated_text", "")
                elif "generated_text" in result:
                    generated_text = result["generated_text"]
                elif "completion" in result:
                    generated_text = result["completion"]
                else:
                    raise LLMError(f"Unexpected response format: {result}")

                if not generated_text:
                    raise LLMError("Empty response from LLM")

                logger.info(
                    f"Successfully generated {len(generated_text.split())} words"
                )

                return generated_text

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM: {e}")
            raise LLMError(f"LLM HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise LLMError(f"Generation failed: {str(e)}")

    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """
        Generate content with separate system and user prompts.

        For Mistral models that support system prompts.

        Args:
            system_prompt: System-level instructions
            user_prompt: User query/prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text content
        """
        # Combine system and user prompts in Mistral format
        # Mistral uses <s>[INST] ... [/INST] format
        combined_prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"

        return await self.generate(
            prompt=combined_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

    async def health_check(self) -> bool:
        """
        Check if LLM service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try a minimal generation to test connectivity
            test_prompt = "Hello"
            await self.generate(
                prompt=test_prompt,
                max_tokens=10,
                temperature=0.5
            )
            return True

        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get or create LLM client singleton.

    Returns:
        LLMClient instance
    """
    global _llm_client

    if _llm_client is None:
        _llm_client = LLMClient()

    return _llm_client
