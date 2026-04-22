"""
Local medical analyzer — symptom analysis via Ollama + MedGemma.

Executes reasoning trace instructions against PHI-complete patient data
using the local MedGemma model.  All processing stays on the local machine.

Input:  ReasoningTrace (from cloud coordinator) + MedicalRecord + Patient
Output: AnalysisResult with entities, risk_level, recommendations

Error handling:
- Model unavailability → raises with clear error
- Malformed output → fallback to raw text analysis
- 30-second timeout on model inference
"""

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.local_agents.ollama_client import OllamaClient

logger = structlog.get_logger(__name__)


@dataclass
class AnalysisResult:
    """Structured result from local medical analysis.

    Attributes:
        entities: Extracted medical entities (symptoms, conditions, etc.).
        risk_level: Assessed risk level (low/medium/high/critical).
        recommendations: Clinical recommendations.
        analysis_text: Full analysis narrative.
        raw_response: Raw model output (for debugging).
    """

    entities: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    recommendations: list[str] = field(default_factory=list)
    analysis_text: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "entities": self.entities,
            "risk_level": self.risk_level,
            "recommendations": self.recommendations,
            "analysis_text": self.analysis_text,
        }


# ── Prompt Template ──────────────────────────────────────────────────────

_ANALYZER_SYSTEM_PROMPT = """\
You are a medical analysis assistant. Analyze the patient's symptoms and \
medical history to identify clinical entities, assess risk, and provide \
recommendations.

Output your analysis as valid JSON with this schema:
{
    "entities": {"key symptom or condition": "clinical detail"},
    "risk_level": "low|medium|high|critical",
    "recommendations": ["recommendation 1", "recommendation 2"],
    "analysis_text": "Narrative clinical analysis paragraph"
}
"""

_ANALYZER_USER_PROMPT = """\
Reasoning Instructions from Coordinator:
{instructions}

Patient Context:
- Age: {age}
- Sex: {sex}
- Known Conditions: {conditions}
- Current Medications: {medications}
- Known Allergies: {allergies}

Current Symptoms:
{symptoms}

Perform the analysis following the reasoning instructions above. \
Output your structured analysis as JSON.
"""


class MedicalAnalyzer:
    """Local medical analyzer executing trace instructions against PHI.

    Uses MedGemma via Ollama to analyze symptoms in the context of
    the patient's full medical profile. All data stays local.

    Attributes:
        _ollama: OllamaClient for model inference.
    """

    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama = ollama_client

    async def analyze(
        self,
        trace: dict[str, Any],
        patient_doc: dict[str, Any],
        symptoms: str,
    ) -> AnalysisResult:
        """Execute a reasoning trace against patient data for symptom analysis.

        Args:
            trace: ReasoningTrace dict with instructions.
            patient_doc: Full patient document from MongoDB (contains PHI).
            symptoms: Raw symptom text from the medical record.

        Returns:
            AnalysisResult with structured clinical insights.

        Raises:
            OllamaUnavailableError: If Ollama is not reachable.
            OllamaTimeoutError: If inference exceeds timeout.
        """
        # Build prompt with full PHI context (local only)
        user_prompt = _ANALYZER_USER_PROMPT.format(
            instructions=trace.get("instructions", "Analyze the symptoms."),
            age=self._calculate_age(patient_doc.get("dob", "")),
            sex=patient_doc.get("sex", "unknown"),
            conditions=", ".join(patient_doc.get("conditions", [])) or "none",
            medications=", ".join(patient_doc.get("medications", [])) or "none",
            allergies=", ".join(patient_doc.get("allergies", [])) or "none",
            symptoms=symptoms,
        )

        await logger.ainfo(
            "medical_analysis_started",
            patient_id=str(patient_doc.get("_id", "unknown")),
            symptoms_length=len(symptoms),
        )

        # Invoke MedGemma
        raw_response = await self._ollama.generate(
            prompt=user_prompt,
            system_prompt=_ANALYZER_SYSTEM_PROMPT,
        )

        # Parse response
        result = self._parse_response(raw_response)

        await logger.ainfo(
            "medical_analysis_completed",
            patient_id=str(patient_doc.get("_id", "unknown")),
            risk_level=result.risk_level,
            entity_count=len(result.entities),
        )

        return result

    def _parse_response(self, response_text: str) -> AnalysisResult:
        """Parse the model response into a structured AnalysisResult.

        Attempts JSON parsing first; falls back to extracting a risk
        level from raw text if JSON parsing fails.

        Args:
            response_text: Raw model output.

        Returns:
            Parsed AnalysisResult.
        """
        # Try to extract JSON from response
        json_text = response_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text

        try:
            parsed = json.loads(json_text)
            return AnalysisResult(
                entities=parsed.get("entities", {}),
                risk_level=self._validate_risk_level(parsed.get("risk_level", "low")),
                recommendations=parsed.get("recommendations", []),
                analysis_text=parsed.get("analysis_text", ""),
                raw_response=response_text,
            )
        except (json.JSONDecodeError, TypeError):
            # Fallback: extract what we can from raw text
            logger.warning(
                "analyzer_json_parse_fallback",
                response_length=len(response_text),
            )
            return AnalysisResult(
                entities={},
                risk_level=self._extract_risk_from_text(response_text),
                recommendations=[],
                analysis_text=response_text,
                raw_response=response_text,
            )

    @staticmethod
    def _validate_risk_level(level: str) -> str:
        """Validate and normalize risk level string."""
        valid_levels = {"low", "medium", "high", "critical"}
        normalized = level.lower().strip()
        return normalized if normalized in valid_levels else "low"

    @staticmethod
    def _extract_risk_from_text(text: str) -> str:
        """Attempt to extract risk level from unstructured text."""
        text_lower = text.lower()
        if "critical" in text_lower:
            return "critical"
        if "high risk" in text_lower or "high-risk" in text_lower:
            return "high"
        if "medium risk" in text_lower or "moderate risk" in text_lower:
            return "medium"
        return "low"

    @staticmethod
    def _calculate_age(dob: Any) -> str:
        """Calculate age from date of birth."""
        from datetime import date

        if not dob:
            return "unknown"
        try:
            if isinstance(dob, str):
                dob = date.fromisoformat(dob)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return str(age)
        except (ValueError, TypeError):
            return "unknown"
