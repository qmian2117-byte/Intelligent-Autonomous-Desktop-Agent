"""
Asynchronous Ollama API client wrapper with health checks,
fallback routing, and structured output support for DesktopPilot AI.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
from loguru import logger

from config.settings import settings
from models.ollama.model_registry import AVAILABLE_LOCAL_MODELS


class OllamaClient:
    """Production-grade Ollama client wrapper."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = settings.DEFAULT_AGENT_MODEL
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def is_healthy(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama server not reachable at {self.base_url}: {e}")
            return False

    async def list_loaded_models(self) -> List[Dict[str, Any]]:
        """Fetch list of models available in the Ollama instance."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to fetch models from Ollama: {e}")
            return []

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send chat messages to Ollama and receive structured response."""
        chosen_model = model or self.default_model

        payload: Dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Ollama chat with model '{chosen_model}': {e}")
            raise

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """Stream chat tokens token-by-token."""
        chosen_model = model or self.default_model
        payload = {
            "model": chosen_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                import json
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        await self._client.aclose()


# Singleton instance
ollama_client = OllamaClient()

