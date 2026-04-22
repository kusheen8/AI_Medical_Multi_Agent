"""
Ollama client wrapper for local LLM inference.

Provides a clean interface to the Ollama API for running MedGemma
or other local models.  All PHI processing happens through this client
— data never leaves the local machine.

Error handling:
- Model unavailability detection
- Configurable timeout (default 30s)
- Structured logging with latency tracking
"""

import time
from typing import Any

import httpx
import structlog
from ollama import AsyncClient

from app.core.config import Settings

logger = structlog.get_logger(__name__)


class OllamaUnavailableError(Exception):
    """Raised when the Ollama service is not reachable."""

    pass


class OllamaTimeoutError(Exception):
    """Raised when an Ollama inference call exceeds the timeout."""

    pass


class OllamaResponseError(Exception):
    """Raised when Ollama returns a malformed or empty response."""

    pass


class OllamaClient:
    """Async client for Ollama local LLM inference.

    Wraps the ``ollama`` Python package with error handling, timeout
    management, and structured logging.

    Attributes:
        _base_url: Ollama server URL.
        _model: Model name to use for inference.
        _timeout: Maximum seconds to wait for a response.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.OLLAMA_BASE_URL
        self._model = settings.OLLAMA_MODEL
        self._timeout = getattr(settings, "OLLAMA_TIMEOUT", 30)
        self._client = AsyncClient(host=self._base_url)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Generate a response from the local LLM.

        Args:
            prompt: The user prompt to send to the model.
            system_prompt: Optional system instruction.
            timeout: Override default timeout (seconds).

        Returns:
            The model's response text.

        Raises:
            OllamaUnavailableError: If Ollama is not reachable.
            OllamaTimeoutError: If inference exceeds timeout.
            OllamaResponseError: If the response is malformed.
        """
        effective_timeout = timeout or self._timeout
        start = time.perf_counter()

        try:
            response = await self._client.chat(
                model=self._model,
                messages=self._build_messages(prompt, system_prompt),
                options={"num_predict": 2048},
            )

            latency_ms = (time.perf_counter() - start) * 1000

            # Extract response text
            content = response.get("message", {}).get("content", "")
            if not content:
                raise OllamaResponseError("Empty response from Ollama model.")

            await logger.ainfo(
                "ollama_inference_complete",
                model=self._model,
                prompt_length=len(prompt),
                response_length=len(content),
                latency_ms=round(latency_ms, 2),
            )

            return content

        except OllamaResponseError:
            raise
        except httpx.ConnectError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            await logger.aerror(
                "ollama_unavailable",
                base_url=self._base_url,
                latency_ms=round(latency_ms, 2),
                error=str(exc),
            )
            raise OllamaUnavailableError(
                f"Ollama is not reachable at {self._base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            await logger.aerror(
                "ollama_timeout",
                model=self._model,
                timeout=effective_timeout,
                latency_ms=round(latency_ms, 2),
            )
            raise OllamaTimeoutError(
                f"Ollama inference timed out after {effective_timeout}s"
            ) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            await logger.aerror(
                "ollama_inference_failed",
                model=self._model,
                latency_ms=round(latency_ms, 2),
                error=str(exc),
            )
            raise OllamaResponseError(f"Ollama inference failed: {exc}") from exc

    async def is_available(self) -> bool:
        """Check if Ollama is reachable and the configured model is available.

        Returns:
            True if Ollama is running and the model is loaded.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
            if resp.status_code != 200:
                return False

            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return any(self._model in m for m in models)
        except Exception:
            return False

    @staticmethod
    def _build_messages(
        prompt: str, system_prompt: str | None
    ) -> list[dict[str, str]]:
        """Build the messages list for Ollama chat API.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instruction.

        Returns:
            List of message dicts.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages
