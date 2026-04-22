"""
Local history summarizer — longitudinal trend analysis via Ollama + MedGemma.

Analyzes patient medical records over a time period to identify patterns,
trends, and generate a timeline summary.  All processing stays local.

Input:  ReasoningTrace + patient_id + date_range
Output: TimelineSummary with key events, patterns, clinical context

Design:
- Fetches historical records with pagination (handles 6-12 months)
- Aggregates temporal data before sending to model
- Handles insufficient data gracefully
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.services.local_agents.ollama_client import OllamaClient

logger = structlog.get_logger(__name__)


@dataclass
class TimelineSummary:
    """Structured result from longitudinal history analysis.

    Attributes:
        key_events: Significant clinical events in the timeline.
        patterns: Detected temporal patterns (trends, recurring issues).
        clinical_context: Overall clinical context narrative.
        record_count: Number of records analyzed.
        date_range: The time period covered.
        raw_response: Raw model output (for debugging).
    """

    key_events: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    clinical_context: str = ""
    record_count: int = 0
    date_range: dict[str, str] = field(default_factory=dict)
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "key_events": self.key_events,
            "patterns": self.patterns,
            "clinical_context": self.clinical_context,
            "record_count": self.record_count,
            "date_range": self.date_range,
        }


class InsufficientDataError(Exception):
    """Raised when there are too few records for meaningful summarization."""

    pass


# ── Prompt Template ──────────────────────────────────────────────────────

_SUMMARIZER_SYSTEM_PROMPT = """\
You are a medical history analyst. Analyze a patient's medical records \
over time to identify patterns, significant events, and clinical trends.

Output your analysis as valid JSON with this schema:
{
    "key_events": [
        {"date": "YYYY-MM-DD", "event": "description", "significance": "low|medium|high"}
    ],
    "patterns": ["pattern description 1", "pattern description 2"],
    "clinical_context": "Overall narrative of patient's health trajectory"
}
"""

_SUMMARIZER_USER_PROMPT = """\
Reasoning Instructions from Coordinator:
{instructions}

Patient Context:
- Age: {age}
- Sex: {sex}
- Known Conditions: {conditions}
- Current Medications: {medications}

Medical Records Timeline ({record_count} records, {date_range}):
{records_summary}

Analyze the medical history following the reasoning instructions above. \
Identify key events, temporal patterns, and provide clinical context. \
Output your structured analysis as JSON.
"""


class HistorySummarizer:
    """Local history summarizer for longitudinal patient analysis.

    Fetches patient medical records over a date range, aggregates
    temporal data, and uses MedGemma to generate a clinical timeline.

    Attributes:
        _ollama: OllamaClient for model inference.
        _record_repo: Repository for medical record queries.
    """

    MIN_RECORDS = 2  # Minimum records needed for meaningful analysis

    def __init__(
        self,
        ollama_client: OllamaClient,
        record_repository: MedicalRecordRepository,
    ) -> None:
        self._ollama = ollama_client
        self._record_repo = record_repository

    async def summarize(
        self,
        trace: dict[str, Any],
        patient_doc: dict[str, Any],
        patient_id: str,
        date_range: dict[str, str] | None = None,
    ) -> TimelineSummary:
        """Execute a reasoning trace for longitudinal history analysis.

        Args:
            trace: ReasoningTrace dict with summarization instructions.
            patient_doc: Full patient document from MongoDB (PHI).
            patient_id: Patient's ObjectId string.
            date_range: Optional dict with 'start' and 'end' date strings.

        Returns:
            TimelineSummary with key events, patterns, and clinical context.

        Raises:
            InsufficientDataError: If fewer than MIN_RECORDS exist.
            OllamaUnavailableError: If Ollama is not reachable.
        """
        # Fetch historical records
        records = await self._fetch_records(patient_id, date_range)

        if len(records) < self.MIN_RECORDS:
            raise InsufficientDataError(
                f"Only {len(records)} records found for patient {patient_id}. "
                f"Need at least {self.MIN_RECORDS} for summarization."
            )

        # Build prompt
        records_summary = self._format_records_for_prompt(records)
        date_range_str = self._format_date_range(date_range, records)

        user_prompt = _SUMMARIZER_USER_PROMPT.format(
            instructions=trace.get("instructions", "Summarize the medical history."),
            age=self._calculate_age(patient_doc.get("dob", "")),
            sex=patient_doc.get("sex", "unknown"),
            conditions=", ".join(patient_doc.get("conditions", [])) or "none",
            medications=", ".join(patient_doc.get("medications", [])) or "none",
            record_count=len(records),
            date_range=date_range_str,
            records_summary=records_summary,
        )

        await logger.ainfo(
            "history_summarization_started",
            patient_id=patient_id,
            record_count=len(records),
        )

        # Invoke MedGemma
        raw_response = await self._ollama.generate(
            prompt=user_prompt,
            system_prompt=_SUMMARIZER_SYSTEM_PROMPT,
        )

        # Parse response
        result = self._parse_response(raw_response, len(records), date_range)

        await logger.ainfo(
            "history_summarization_completed",
            patient_id=patient_id,
            key_events_count=len(result.key_events),
            patterns_count=len(result.patterns),
        )

        return result

    async def _fetch_records(
        self, patient_id: str, date_range: dict[str, str] | None
    ) -> list[dict[str, Any]]:
        """Fetch medical records for a patient, with optional date filtering.

        Uses pagination to handle large record sets efficiently.
        """
        records: list[dict[str, Any]] = []
        page = 1
        page_size = 50

        while True:
            result = await self._record_repo.list_by_patient_id(
                patient_id=patient_id,
                page=page,
                page_size=page_size,
            )
            items = result.get("items", [])
            if not items:
                break

            # Filter by date range if provided
            if date_range:
                items = self._filter_by_date_range(items, date_range)

            records.extend(items)
            page += 1

            # Stop if we've fetched all pages
            if page > result.get("pages", 1):
                break

        return records

    @staticmethod
    def _filter_by_date_range(
        records: list[dict[str, Any]], date_range: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Filter records to those within the specified date range."""
        filtered = []
        start = date_range.get("start")
        end = date_range.get("end")

        for record in records:
            created = record.get("created_at")
            if created is None:
                continue

            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except ValueError:
                    continue

            if start:
                try:
                    start_dt = datetime.fromisoformat(start)
                    if created.replace(tzinfo=None) < start_dt.replace(tzinfo=None):
                        continue
                except ValueError:
                    pass

            if end:
                try:
                    end_dt = datetime.fromisoformat(end)
                    if created.replace(tzinfo=None) > end_dt.replace(tzinfo=None):
                        continue
                except ValueError:
                    pass

            filtered.append(record)

        return filtered

    @staticmethod
    def _format_records_for_prompt(records: list[dict[str, Any]]) -> str:
        """Format medical records into a concise text summary for the prompt."""
        lines: list[str] = []
        for i, record in enumerate(records, 1):
            created = record.get("created_at", "unknown date")
            if isinstance(created, datetime):
                created = created.strftime("%Y-%m-%d")
            symptoms = record.get("symptoms", "no symptoms recorded")
            risk = record.get("risk_level", "not assessed")
            analysis = record.get("analysis_result", "")

            entry = f"Record {i} ({created}): Symptoms: {symptoms}"
            if risk and risk != "not assessed":
                entry += f" | Risk: {risk}"
            if analysis:
                entry += f" | Analysis: {analysis[:200]}"
            lines.append(entry)

        return "\n".join(lines)

    @staticmethod
    def _format_date_range(
        date_range: dict[str, str] | None, records: list[dict[str, Any]]
    ) -> str:
        """Format the date range as a human-readable string."""
        if date_range:
            return f"{date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}"

        # Infer from records
        dates = []
        for r in records:
            created = r.get("created_at")
            if isinstance(created, datetime):
                dates.append(created)
        if dates:
            return f"{min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}"
        return "unknown period"

    def _parse_response(
        self,
        response_text: str,
        record_count: int,
        date_range: dict[str, str] | None,
    ) -> TimelineSummary:
        """Parse the model response into a structured TimelineSummary."""
        json_text = response_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text

        try:
            parsed = json.loads(json_text)
            return TimelineSummary(
                key_events=parsed.get("key_events", []),
                patterns=parsed.get("patterns", []),
                clinical_context=parsed.get("clinical_context", ""),
                record_count=record_count,
                date_range=date_range or {},
                raw_response=response_text,
            )
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "summarizer_json_parse_fallback",
                response_length=len(response_text),
            )
            return TimelineSummary(
                key_events=[],
                patterns=[],
                clinical_context=response_text,
                record_count=record_count,
                date_range=date_range or {},
                raw_response=response_text,
            )

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
