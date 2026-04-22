"""
Gemini-based cloud coordinator for reasoning trace generation.

Generates ReasoningTraces from de-identified patient context using the
Gemini API.  All inputs are validated to contain NO PHI before sending
to the cloud.

Uses the ``google-genai`` SDK (NOT the deprecated ``google-generativeai``).

Error handling:
- 5-second timeout on API calls
- Exponential backoff retry (max 3 attempts)
- Rate limit detection and backoff
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.privacy import PHILeakageError, validate_cloud_payload
from app.services.coordinator.prompts import (
    format_history_summarization_prompt,
    format_symptom_analysis_prompt,
)
from app.services.privacy_filter import PrivacyFilter

logger = structlog.get_logger(__name__)

# Default trace expiration (24 hours)
_DEFAULT_TRACE_TTL_HOURS = 24


class CoordinatorError(Exception):
    """Base exception for coordinator failures."""

    pass


class CoordinatorTimeoutError(CoordinatorError):
    """Raised when the Gemini API call times out."""

    pass


class CoordinatorRateLimitError(CoordinatorError):
    """Raised when the Gemini API rate limit is hit."""

    pass


class GeminiCoordinator:
    """Cloud coordinator that generates reasoning traces via Gemini.

    All patient data is de-identified before being sent to Gemini.
    The coordinator produces structured reasoning instructions that
    the local agents (MedGemma/Ollama) execute against PHI.

    Attributes:
        _client: google-genai client instance.
        _model: Gemini model name to use.
        _privacy_filter: PrivacyFilter for de-identification.
        _timeout: API call timeout in seconds.
        _max_retries: Maximum retry attempts.
    """

    def __init__(
        self,
        settings: Settings,
        privacy_filter: PrivacyFilter | None = None,
    ) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        self._privacy_filter = privacy_filter or PrivacyFilter()
        self._timeout = getattr(settings, "COORDINATOR_TIMEOUT", 5)
        self._max_retries = 3

    async def generate_reasoning_trace(
        self,
        task_type: str,
        patient_doc: dict[str, Any],
        symptoms: str | None = None,
        date_range: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generate a reasoning trace from de-identified patient context.

        This is the main entry point for the coordinator. It:
        1. De-identifies the patient data
        2. Validates no PHI in the payload
        3. Calls Gemini to generate reasoning instructions
        4. Parses the structured output
        5. Returns a complete trace creation dict

        Args:
            task_type: "symptom_analysis" or "history_summarization".
            patient_doc: Raw patient document from MongoDB.
            symptoms: Raw symptom text (will be de-identified).
            date_range: Optional date range for history queries.

        Returns:
            Dict suitable for creating a ReasoningTrace in the DB.

        Raises:
            PHILeakageError: If PHI is detected in cloud-bound data.
            CoordinatorTimeoutError: If Gemini doesn't respond in time.
            CoordinatorError: On other Gemini API failures.
        """
        # Step 1: De-identify
        context = self._privacy_filter.prepare_coordinator_context(
            patient_doc=patient_doc,
            symptoms=symptoms,
            date_range=date_range,
        )

        # Step 2: Format prompt
        if task_type == "symptom_analysis":
            system_prompt, user_prompt = format_symptom_analysis_prompt(context)
        elif task_type == "history_summarization":
            system_prompt, user_prompt = format_history_summarization_prompt(context)
        else:
            raise CoordinatorError(f"Unknown task type: {task_type}")

        # Step 3: Final PHI validation on the prompt
        validate_cloud_payload(user_prompt)

        # Step 4: Call Gemini with retry
        response_text = await self._call_gemini_with_retry(system_prompt, user_prompt)

        # Step 5: Parse response
        trace_data = self._parse_response(response_text, task_type)

        await logger.ainfo(
            "reasoning_trace_generated",
            task_type=task_type,
            trace_keys=list(trace_data.keys()),
        )

        return trace_data

    async def _call_gemini_with_retry(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Call Gemini API with exponential backoff retry.

        Args:
            system_prompt: System instruction for the model.
            user_prompt: User message with de-identified context.

        Returns:
            Raw response text from Gemini.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await asyncio.wait_for(
                    self._call_gemini(system_prompt, user_prompt),
                    timeout=self._timeout,
                )
                return response
            except asyncio.TimeoutError:
                last_error = CoordinatorTimeoutError(
                    f"Gemini API timed out after {self._timeout}s (attempt {attempt + 1})"
                )
                await logger.awarning(
                    "coordinator_timeout",
                    attempt=attempt + 1,
                    timeout=self._timeout,
                )
            except Exception as exc:
                error_str = str(exc).lower()
                if "429" in error_str or "rate" in error_str:
                    last_error = CoordinatorRateLimitError(str(exc))
                    await logger.awarning(
                        "coordinator_rate_limited",
                        attempt=attempt + 1,
                    )
                else:
                    last_error = CoordinatorError(f"Gemini API error: {exc}")
                    await logger.awarning(
                        "coordinator_error",
                        attempt=attempt + 1,
                        error=str(exc),
                    )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self._max_retries - 1:
                backoff = 2 ** attempt
                await asyncio.sleep(backoff)

        raise last_error or CoordinatorError("All retry attempts exhausted")

    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Make a single Gemini API call.

        Args:
            system_prompt: System instruction.
            user_prompt: User message.

        Returns:
            Response text.
        """
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,  # Low temperature for deterministic output
                max_output_tokens=1024,
            ),
        )
        return response.text or ""

    def _parse_response(self, response_text: str, task_type: str) -> dict[str, Any]:
        """Parse Gemini response into a reasoning trace dict.

        Attempts JSON parsing first; falls back to wrapping raw text
        as instructions if JSON parsing fails.

        Args:
            response_text: Raw response from Gemini.
            task_type: The type of analysis task.

        Returns:
            Dict with trace fields.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=_DEFAULT_TRACE_TTL_HOURS)

        # Try to extract JSON from response (might be wrapped in markdown code blocks)
        json_text = response_text.strip()
        if json_text.startswith("```"):
            # Strip markdown code block
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text

        try:
            parsed = json.loads(json_text)
            instructions = parsed.get("instructions", response_text)
            allowed_data_classes = parsed.get("allowed_data_classes", [])
        except (json.JSONDecodeError, TypeError):
            # Fallback: use raw text as instructions
            instructions = response_text
            allowed_data_classes = ["vitals", "symptoms", "medications", "history"]
            logger.warning(
                "coordinator_json_parse_fallback",
                task_type=task_type,
                response_length=len(response_text),
            )

        return {
            "task_type": task_type,
            "instructions": instructions,
            "allowed_data_classes": allowed_data_classes,
            "origin": "gemini_coordinator",
            "expires_at": expires_at,
        }
