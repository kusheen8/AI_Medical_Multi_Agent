"""
Version-controlled prompt templates for the cloud coordinator.

Each template accepts ONLY de-identified context variables — never raw PHI.
Templates include explicit instructions to avoid generating patient identifiers.

Prompt design principles:
- Deterministic: same input produces same reasoning trace structure
- Safe: no PHI in input variables; instructions forbid identifier generation
- Structured: output is parseable into ReasoningTrace fields
"""

# ── Symptom Analysis Prompt ──────────────────────────────────────────────

SYMPTOM_ANALYSIS_SYSTEM_PROMPT = """\
You are a medical reasoning coordinator. Your role is to generate structured \
reasoning instructions for a local medical analyzer agent.

CRITICAL RULES:
1. Do NOT include any patient names, dates of birth, addresses, or identifiers.
2. Do NOT include any specific symptom text — only categories are provided.
3. Your output is a REASONING TRACE — instructions for analysis, not the analysis itself.
4. Output MUST be valid JSON matching the schema below.

Output JSON Schema:
{
    "instructions": "Step-by-step reasoning instructions for the local analyzer",
    "allowed_data_classes": ["list", "of", "data", "categories", "the", "analyzer", "may", "access"],
    "focus_areas": ["list", "of", "clinical", "areas", "to", "prioritize"],
    "risk_assessment_criteria": "Criteria for determining risk level",
    "recommended_analyses": ["list", "of", "analyses", "to", "perform"]
}
"""

SYMPTOM_ANALYSIS_USER_PROMPT = """\
Generate a reasoning trace for symptom analysis with the following de-identified context:

Patient Profile:
- Age bracket: {age_bracket}
- Sex: {sex}
- Condition categories: {condition_categories}
- Medication count: {medication_count}
- Has known allergies: {has_allergies}

Symptom Information:
- {symptom_categories}

Task: Generate step-by-step instructions for a local medical analyzer to:
1. Analyze the patient's symptoms in context of their medical profile
2. Identify potential risk factors and clinical entities
3. Assess risk level (low/medium/high/critical)
4. Generate clinical recommendations

Remember: Output ONLY the JSON reasoning trace. No patient identifiers.
"""


# ── History Summarization Prompt ─────────────────────────────────────────

HISTORY_SUMMARIZATION_SYSTEM_PROMPT = """\
You are a medical reasoning coordinator. Your role is to generate structured \
reasoning instructions for a local history summarization agent.

CRITICAL RULES:
1. Do NOT include any patient names, dates of birth, addresses, or identifiers.
2. Your output is a REASONING TRACE — instructions for summarization, not the summary itself.
3. Output MUST be valid JSON matching the schema below.

Output JSON Schema:
{
    "instructions": "Step-by-step reasoning instructions for the local summarizer",
    "allowed_data_classes": ["list", "of", "data", "categories", "the", "summarizer", "may", "access"],
    "temporal_focus": "What time periods to emphasize",
    "pattern_detection_criteria": "What patterns to look for in longitudinal data",
    "summary_structure": "How to structure the output timeline summary"
}
"""

HISTORY_SUMMARIZATION_USER_PROMPT = """\
Generate a reasoning trace for history summarization with the following de-identified context:

Patient Profile:
- Age bracket: {age_bracket}
- Sex: {sex}
- Condition categories: {condition_categories}
- Medication count: {medication_count}
- Has known allergies: {has_allergies}

Analysis Period:
- Date range: {date_range}

Task: Generate step-by-step instructions for a local history summarizer to:
1. Aggregate patient records over the specified time period
2. Identify temporal patterns (symptom trends, risk level changes)
3. Detect significant clinical events or transitions
4. Generate a structured timeline summary with clinical insights

Remember: Output ONLY the JSON reasoning trace. No patient identifiers.
"""


def format_symptom_analysis_prompt(context: dict) -> tuple[str, str]:
    """Format the symptom analysis prompt with de-identified context.

    Args:
        context: De-identified patient context from PrivacyFilter.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    user_prompt = SYMPTOM_ANALYSIS_USER_PROMPT.format(
        age_bracket=context.get("age_bracket", "unknown"),
        sex=context.get("sex", "unknown"),
        condition_categories=", ".join(context.get("condition_categories", [])) or "none",
        medication_count=context.get("medication_count", 0),
        has_allergies=context.get("has_allergies", False),
        symptom_categories=context.get("symptom_categories", "unspecified"),
    )
    return SYMPTOM_ANALYSIS_SYSTEM_PROMPT, user_prompt


def format_history_summarization_prompt(context: dict) -> tuple[str, str]:
    """Format the history summarization prompt with de-identified context.

    Args:
        context: De-identified patient context from PrivacyFilter.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    date_range = context.get("date_range", {})
    date_range_str = f"{date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}"

    user_prompt = HISTORY_SUMMARIZATION_USER_PROMPT.format(
        age_bracket=context.get("age_bracket", "unknown"),
        sex=context.get("sex", "unknown"),
        condition_categories=", ".join(context.get("condition_categories", [])) or "none",
        medication_count=context.get("medication_count", 0),
        has_allergies=context.get("has_allergies", False),
        date_range=date_range_str,
    )
    return HISTORY_SUMMARIZATION_SYSTEM_PROMPT, user_prompt
