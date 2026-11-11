"""
LLM Service Layer for DesktopPilot AI.
Provides local model inference via Ollama (Llama 3.1 8B).
Strictly offline, zero cloud API dependencies.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional
try:
    import httpx
except ImportError:
    httpx = None

import urllib.request
import json
import time
from utils.logger import logger
from config.settings import settings


class LLMService:
    """Local LLM Service communicating directly with the Ollama server."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        # Use a fast 4.5s timeout so CPU-bound Ollama never freezes the agent for 60s
        self.timeout = min(timeout or 4.5, 4.5)
        self._circuit_open_until: float = 0.0
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) if httpx else None

    async def check_health(self) -> Dict[str, Any]:
        """Verify Ollama server status and verify if Llama 3.1 8B is installed."""
        if not self._client:
            try:
                req = urllib.request.Request(f"{self.base_url}/api/tags")
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    models = [m.get("name") for m in data.get("models", [])]
                    is_model_present = any(self.model in name for name in models)
                    return {
                        "status": "healthy" if is_model_present else "model_missing",
                        "installed_models": models,
                        "target_model": self.model,
                        "ready": is_model_present
                    }
            except Exception as e:
                return {"status": "offline", "message": f"Ollama not reachable: {e}", "ready": False}

        try:
            response = await self._client.get("/api/tags")
            if response.status_code != 200:
                return {"status": "unhealthy", "message": "Ollama server returned non-200 status"}

            models = response.json().get("models", [])
            installed_models = [m.get("name") for m in models]
            is_model_present = any(self.model in name for name in installed_models)

            return {
                "status": "healthy" if is_model_present else "model_missing",
                "installed_models": installed_models,
                "target_model": self.model,
                "ready": is_model_present,
            }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "message": f"Could not connect to Ollama at {self.base_url}. Is Ollama running?",
                "ready": False,
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "ready": False}

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a multi-turn conversation or agent task to Llama 3.1 8B.
        """
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE
            },
        }

        # Fast circuit breaker: if Ollama timed out recently, skip immediately
        if time.time() < self._circuit_open_until:
            raise TimeoutError("Ollama circuit breaker open (CPU timeout bypass)")

        if not self._client:
            try:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/api/chat",
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode())
                    return data.get("message", {}).get("content", "")
            except Exception as e:
                self._circuit_open_until = time.time() + 180.0
                logger.warning(f"Ollama fast timeout/bypass ({e}) -> switching to instant local engine.")
                raise

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            self._circuit_open_until = time.time() + 180.0
            logger.warning(f"LLMService fast timeout/bypass ({e}) -> switching to instant local engine.")
            raise

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens in real-time for live agent output."""
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "stream": True,
            "options": {"temperature": settings.LLM_TEMPERATURE},
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                import json
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue

    async def close(self) -> None:
        """Cleanly close the HTTP client connection."""
        await self._client.aclose()


# Global service instance for the agent
llm_service = LLMService()

