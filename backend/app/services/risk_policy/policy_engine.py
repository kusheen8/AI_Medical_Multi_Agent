"""
Risk policy engine — evaluates analysis results against configurable rules.

Loads active policy rules from MongoDB and evaluates them against
analysis results to determine whether alerts should be triggered.

Supports three condition types:
- risk_threshold: simple level comparison
- emergency_pattern: symptom keyword matching
- consecutive_high: checks N consecutive high-risk records

Dry-run mode allows testing rules without creating actual alerts.
"""

from typing import Any

import structlog

from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.policy_repository import PolicyRepository
from app.models.policy_rule import (
    AlertTrigger,
    ConditionType,
    PolicyAction,
    RiskTier,
)

logger = structlog.get_logger(__name__)

# Risk tier ordering for comparison (higher index = higher severity)
_RISK_ORDER: dict[str, int] = {
    RiskTier.LOW.value: 0,
    RiskTier.MEDIUM.value: 1,
    RiskTier.HIGH.value: 2,
    RiskTier.CRITICAL.value: 3,
}

# Known emergency symptom patterns
_EMERGENCY_PATTERNS: list[list[str]] = [
    ["chest pain", "shortness of breath"],
    ["severe headache", "vision loss"],
    ["unresponsive", "no pulse"],
    ["difficulty breathing", "cyanosis"],
    ["seizure", "unconscious"],
    ["severe bleeding", "hemorrhage"],
    ["anaphylaxis", "allergic reaction", "swelling"],
    ["stroke", "facial drooping", "arm weakness", "speech difficulty"],
]


class PolicyEngine:
    """Evaluates analysis results against active policy rules.

    Attributes:
        _policy_repo: Repository for loading policy rules.
        _record_repo: Repository for querying patient record history.
        _global_dry_run: If True, all evaluations are dry-run only.
    """

    def __init__(
        self,
        policy_repo: PolicyRepository,
        record_repo: MedicalRecordRepository,
        global_dry_run: bool = False,
    ) -> None:
        self._policy_repo = policy_repo
        self._record_repo = record_repo
        self._global_dry_run = global_dry_run

    async def evaluate(
        self,
        patient_id: str,
        risk_level: str,
        symptoms: str,
        analysis_result: dict[str, Any] | None = None,
    ) -> list[AlertTrigger]:
        """Evaluate all active rules against the given analysis context.

        Args:
            patient_id: Patient whose analysis just completed.
            risk_level: Assessed risk level (low/medium/high/critical).
            symptoms: Original symptom text.
            analysis_result: Full analysis result dict (optional).

        Returns:
            List of AlertTrigger objects for rules that matched.
        """
        rules = await self._policy_repo.get_active_rules()
        if not rules:
            await logger.ainfo("policy_no_active_rules")
            return []

        triggers: list[AlertTrigger] = []
        for rule in rules:
            try:
                trigger = await self._evaluate_rule(
                    rule, patient_id, risk_level, symptoms, analysis_result
                )
                if trigger is not None:
                    triggers.append(trigger)
            except Exception:
                await logger.aerror(
                    "policy_rule_evaluation_error",
                    rule_id=str(rule.get("_id", "")),
                    rule_name=rule.get("name", ""),
                    exc_info=True,
                )

        if triggers:
            await logger.ainfo(
                "policy_evaluation_complete",
                patient_id=patient_id,
                risk_level=risk_level,
                triggers_count=len(triggers),
                dry_run_count=sum(1 for t in triggers if t.dry_run),
            )

        return triggers

    async def _evaluate_rule(
        self,
        rule: dict[str, Any],
        patient_id: str,
        risk_level: str,
        symptoms: str,
        analysis_result: dict[str, Any] | None,
    ) -> AlertTrigger | None:
        """Evaluate a single policy rule.

        Returns:
            An AlertTrigger if the rule matches, or None.
        """
        condition_type = rule.get("condition_type", "")
        matched = False
        reason = ""

        if condition_type == ConditionType.RISK_THRESHOLD.value:
            matched, reason = self._evaluate_threshold(rule, risk_level)
        elif condition_type == ConditionType.EMERGENCY_PATTERN.value:
            matched, reason = self._evaluate_emergency_pattern(rule, symptoms)
        elif condition_type == ConditionType.CONSECUTIVE_HIGH.value:
            matched, reason = await self._evaluate_consecutive(rule, patient_id)
        else:
            await logger.awarning(
                "policy_unknown_condition_type",
                condition_type=condition_type,
                rule_name=rule.get("name", ""),
            )
            return None

        if not matched:
            return None

        is_dry_run = self._global_dry_run or rule.get("dry_run", False)

        return AlertTrigger(
            rule_id=str(rule["_id"]),
            rule_name=rule.get("name", ""),
            action=PolicyAction(rule.get("action", PolicyAction.ALERT.value)),
            severity=rule.get("severity", "critical"),
            channels=rule.get("channels", ["sms", "email"]),
            reason=reason,
            dry_run=is_dry_run,
        )

    def _evaluate_threshold(
        self, rule: dict[str, Any], risk_level: str
    ) -> tuple[bool, str]:
        """Check if the risk level meets or exceeds the rule's threshold.

        Args:
            rule: The policy rule document.
            risk_level: The assessed risk level.

        Returns:
            Tuple of (matched, reason).
        """
        rule_risk = rule.get("risk_level", "critical")
        params = rule.get("threshold_params", {})
        min_level = params.get("min_risk_level", rule_risk)

        current_order = _RISK_ORDER.get(risk_level, -1)
        threshold_order = _RISK_ORDER.get(min_level, 99)

        if current_order >= threshold_order:
            return True, (
                f"Risk level '{risk_level}' meets threshold "
                f"'{min_level}' for rule '{rule.get('name', '')}'"
            )
        return False, ""

    def _evaluate_emergency_pattern(
        self, rule: dict[str, Any], symptoms: str
    ) -> tuple[bool, str]:
        """Check if symptoms match any known emergency patterns.

        Args:
            rule: The policy rule document.
            symptoms: The symptom text to check.

        Returns:
            Tuple of (matched, reason).
        """
        params = rule.get("threshold_params", {})
        custom_patterns: list[list[str]] = params.get("patterns", [])
        patterns_to_check = custom_patterns if custom_patterns else _EMERGENCY_PATTERNS

        symptoms_lower = symptoms.lower()

        for pattern in patterns_to_check:
            matching_keywords = [kw for kw in pattern if kw.lower() in symptoms_lower]
            # Require at least 2 keywords from the pattern to match,
            # or all keywords if the pattern has only 1
            match_threshold = min(2, len(pattern))
            if len(matching_keywords) >= match_threshold:
                return True, (
                    f"Emergency pattern matched: {matching_keywords} "
                    f"(from pattern: {pattern})"
                )
        return False, ""

    async def _evaluate_consecutive(
        self, rule: dict[str, Any], patient_id: str
    ) -> tuple[bool, str]:
        """Check if patient has N consecutive high-risk records.

        Args:
            rule: The policy rule document.
            patient_id: The patient to check.

        Returns:
            Tuple of (matched, reason).
        """
        params = rule.get("threshold_params", {})
        required_count = params.get("consecutive_count", 3)
        check_level = params.get("check_level", "high")

        # Fetch recent records (up to required_count + buffer)
        result = await self._record_repo.list_by_patient_id(
            patient_id=patient_id,
            page=1,
            page_size=required_count + 2,
        )
        records = result.get("items", [])

        if len(records) < required_count:
            return False, ""

        # Check if the most recent N records are all at or above check_level
        check_order = _RISK_ORDER.get(check_level, 2)
        consecutive = 0
        for record in records[:required_count]:
            record_risk = record.get("risk_level", "low")
            if _RISK_ORDER.get(record_risk, 0) >= check_order:
                consecutive += 1
            else:
                break

        if consecutive >= required_count:
            return True, (
                f"{consecutive} consecutive records at or above "
                f"'{check_level}' risk level (threshold: {required_count})"
            )
        return False, ""

    async def seed_default_policies(self) -> int:
        """Seed the database with default policy rules if none exist.

        Returns:
            Number of policies seeded.
        """
        existing = await self._policy_repo.get_active_rules()
        if existing:
            await logger.ainfo("policy_seed_skipped", existing_count=len(existing))
            return 0

        default_rules = [
            {
                "name": "Critical Risk Emergency Alert",
                "description": "Immediate alert for critical risk assessments.",
                "condition_type": ConditionType.RISK_THRESHOLD.value,
                "risk_level": RiskTier.CRITICAL.value,
                "threshold_params": {"min_risk_level": "critical"},
                "action": PolicyAction.ESCALATE.value,
                "severity": "critical",
                "channels": ["sms", "email", "push"],
                "enabled": True,
                "dry_run": False,
                "version": 1,
            },
            {
                "name": "High Risk Urgent Alert",
                "description": "Urgent notification for high risk assessments.",
                "condition_type": ConditionType.RISK_THRESHOLD.value,
                "risk_level": RiskTier.HIGH.value,
                "threshold_params": {"min_risk_level": "high"},
                "action": PolicyAction.ALERT.value,
                "severity": "error",
                "channels": ["sms", "email"],
                "enabled": True,
                "dry_run": False,
                "version": 1,
            },
            {
                "name": "Medium Risk Info Notification",
                "description": "Informational notification for medium risk assessments.",
                "condition_type": ConditionType.RISK_THRESHOLD.value,
                "risk_level": RiskTier.MEDIUM.value,
                "threshold_params": {"min_risk_level": "medium"},
                "action": PolicyAction.INFO.value,
                "severity": "warning",
                "channels": ["email"],
                "enabled": True,
                "dry_run": False,
                "version": 1,
            },
            {
                "name": "Emergency Symptom Pattern",
                "description": "Immediate alert when symptoms match known emergency patterns.",
                "condition_type": ConditionType.EMERGENCY_PATTERN.value,
                "risk_level": RiskTier.HIGH.value,
                "threshold_params": {"patterns": []},
                "action": PolicyAction.ESCALATE.value,
                "severity": "critical",
                "channels": ["sms", "email", "push"],
                "enabled": True,
                "dry_run": False,
                "version": 1,
            },
            {
                "name": "Consecutive High Risk Escalation",
                "description": "Escalate when 3+ consecutive records are high risk.",
                "condition_type": ConditionType.CONSECUTIVE_HIGH.value,
                "risk_level": RiskTier.HIGH.value,
                "threshold_params": {"consecutive_count": 3, "check_level": "high"},
                "action": PolicyAction.ESCALATE.value,
                "severity": "critical",
                "channels": ["sms", "email"],
                "enabled": True,
                "dry_run": False,
                "version": 1,
            },
        ]

        seeded = 0
        for rule_data in default_rules:
            await self._policy_repo.create(rule_data)
            seeded += 1

        await logger.ainfo("policy_seed_complete", count=seeded)
        return seeded
