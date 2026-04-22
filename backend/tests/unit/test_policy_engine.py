"""
Unit tests for the risk policy engine.

Tests all rule evaluation types, dry-run mode, policy versioning,
and edge cases like no active rules or disabled rules.
"""

import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from app.models.policy_rule import AlertTrigger, ConditionType, PolicyAction, RiskTier
from app.services.risk_policy.policy_engine import PolicyEngine


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_rule(
    name: str = "Test Rule",
    condition_type: str = "risk_threshold",
    risk_level: str = "critical",
    threshold_params: dict | None = None,
    action: str = "alert",
    severity: str = "critical",
    channels: list[str] | None = None,
    enabled: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    return {
        "_id": ObjectId(),
        "name": name,
        "condition_type": condition_type,
        "risk_level": risk_level,
        "threshold_params": threshold_params or {"min_risk_level": risk_level},
        "action": action,
        "severity": severity,
        "channels": channels or ["sms", "email"],
        "enabled": enabled,
        "dry_run": dry_run,
        "version": 1,
    }


def _make_engine(
    rules: list[dict] | None = None,
    records: list[dict] | None = None,
    global_dry_run: bool = False,
) -> PolicyEngine:
    policy_repo = MagicMock()
    policy_repo.get_active_rules = AsyncMock(return_value=rules or [])
    policy_repo.create = AsyncMock()

    record_repo = MagicMock()
    record_items = records or []
    record_repo.list_by_patient_id = AsyncMock(return_value={
        "items": record_items,
        "total": len(record_items),
        "page": 1,
        "page_size": 20,
        "pages": 1,
    })

    return PolicyEngine(
        policy_repo=policy_repo,
        record_repo=record_repo,
        global_dry_run=global_dry_run,
    )


# ── Risk Threshold Tests ────────────────────────────────────────────────


class TestRiskThresholdRules:
    """Tests for risk_threshold condition type."""

    @pytest.mark.asyncio
    async def test_critical_level_triggers_critical_rule(self):
        engine = _make_engine(rules=[_make_rule(risk_level="critical")])
        triggers = await engine.evaluate("patient-1", "critical", "chest pain")
        assert len(triggers) == 1
        assert triggers[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_high_level_triggers_high_rule(self):
        engine = _make_engine(rules=[_make_rule(
            risk_level="high",
            threshold_params={"min_risk_level": "high"},
            severity="error",
        )])
        triggers = await engine.evaluate("patient-1", "high", "headache")
        assert len(triggers) == 1
        assert triggers[0].severity == "error"

    @pytest.mark.asyncio
    async def test_low_level_does_not_trigger_high_rule(self):
        engine = _make_engine(rules=[_make_rule(
            risk_level="high",
            threshold_params={"min_risk_level": "high"},
        )])
        triggers = await engine.evaluate("patient-1", "low", "mild headache")
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_critical_triggers_medium_rule(self):
        """Critical risk should satisfy a medium threshold."""
        engine = _make_engine(rules=[_make_rule(
            risk_level="medium",
            threshold_params={"min_risk_level": "medium"},
            severity="warning",
        )])
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 1

    @pytest.mark.asyncio
    async def test_multiple_rules_can_trigger(self):
        engine = _make_engine(rules=[
            _make_rule(name="High rule", risk_level="high",
                       threshold_params={"min_risk_level": "high"}, severity="error"),
            _make_rule(name="Medium rule", risk_level="medium",
                       threshold_params={"min_risk_level": "medium"}, severity="warning"),
        ])
        triggers = await engine.evaluate("patient-1", "high", "symptoms")
        assert len(triggers) == 2


# ── Emergency Pattern Tests ──────────────────────────────────────────────


class TestEmergencyPatternRules:
    """Tests for emergency_pattern condition type."""

    @pytest.mark.asyncio
    async def test_builtin_pattern_chest_pain_sob(self):
        engine = _make_engine(rules=[_make_rule(
            name="Emergency",
            condition_type="emergency_pattern",
        )])
        triggers = await engine.evaluate(
            "patient-1", "high", "chest pain with shortness of breath"
        )
        assert len(triggers) == 1
        assert "chest pain" in triggers[0].reason.lower()

    @pytest.mark.asyncio
    async def test_no_match_on_unrelated_symptoms(self):
        engine = _make_engine(rules=[_make_rule(
            name="Emergency",
            condition_type="emergency_pattern",
        )])
        triggers = await engine.evaluate(
            "patient-1", "low", "mild headache"
        )
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_custom_pattern_matching(self):
        engine = _make_engine(rules=[_make_rule(
            name="Custom Emergency",
            condition_type="emergency_pattern",
            threshold_params={"patterns": [["fever", "rash"]]},
        )])
        triggers = await engine.evaluate(
            "patient-1", "medium", "high fever with rash"
        )
        assert len(triggers) == 1

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        engine = _make_engine(rules=[_make_rule(
            name="Emergency",
            condition_type="emergency_pattern",
        )])
        triggers = await engine.evaluate(
            "patient-1", "high", "CHEST PAIN and SHORTNESS OF BREATH"
        )
        assert len(triggers) == 1


# ── Consecutive High Tests ───────────────────────────────────────────────


class TestConsecutiveHighRules:
    """Tests for consecutive_high condition type."""

    @pytest.mark.asyncio
    async def test_three_consecutive_high_triggers(self):
        records = [
            {"risk_level": "high", "_id": ObjectId()},
            {"risk_level": "high", "_id": ObjectId()},
            {"risk_level": "high", "_id": ObjectId()},
        ]
        engine = _make_engine(
            rules=[_make_rule(
                name="Consecutive",
                condition_type="consecutive_high",
                threshold_params={"consecutive_count": 3, "check_level": "high"},
            )],
            records=records,
        )
        triggers = await engine.evaluate("patient-1", "high", "symptoms")
        assert len(triggers) == 1

    @pytest.mark.asyncio
    async def test_two_consecutive_does_not_trigger_for_three(self):
        records = [
            {"risk_level": "high", "_id": ObjectId()},
            {"risk_level": "high", "_id": ObjectId()},
            {"risk_level": "low", "_id": ObjectId()},
        ]
        engine = _make_engine(
            rules=[_make_rule(
                name="Consecutive",
                condition_type="consecutive_high",
                threshold_params={"consecutive_count": 3, "check_level": "high"},
            )],
            records=records,
        )
        triggers = await engine.evaluate("patient-1", "high", "symptoms")
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_insufficient_records(self):
        records = [{"risk_level": "high", "_id": ObjectId()}]
        engine = _make_engine(
            rules=[_make_rule(
                name="Consecutive",
                condition_type="consecutive_high",
                threshold_params={"consecutive_count": 3, "check_level": "high"},
            )],
            records=records,
        )
        triggers = await engine.evaluate("patient-1", "high", "symptoms")
        assert len(triggers) == 0


# ── Dry-Run Tests ────────────────────────────────────────────────────────


class TestDryRunMode:
    """Tests for dry-run evaluation."""

    @pytest.mark.asyncio
    async def test_rule_level_dry_run(self):
        engine = _make_engine(rules=[_make_rule(dry_run=True)])
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 1
        assert triggers[0].dry_run is True

    @pytest.mark.asyncio
    async def test_global_dry_run(self):
        engine = _make_engine(
            rules=[_make_rule(dry_run=False)],
            global_dry_run=True,
        )
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 1
        assert triggers[0].dry_run is True

    @pytest.mark.asyncio
    async def test_no_dry_run(self):
        engine = _make_engine(rules=[_make_rule(dry_run=False)])
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 1
        assert triggers[0].dry_run is False


# ── Edge Cases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_no_active_rules(self):
        engine = _make_engine(rules=[])
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_unknown_condition_type(self):
        engine = _make_engine(rules=[_make_rule(condition_type="unknown_type")])
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_rule_evaluation_error_logged_not_raised(self):
        """An error in one rule should not prevent other rules from evaluating."""
        bad_rule = _make_rule(name="Bad Rule")
        bad_rule.pop("threshold_params")  # Will cause an error
        good_rule = _make_rule(name="Good Rule")

        engine = _make_engine(rules=[bad_rule, good_rule])
        # Should not raise; bad rule is skipped
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        # Good rule should still trigger
        assert any(t.rule_name == "Good Rule" for t in triggers)

    @pytest.mark.asyncio
    async def test_trigger_contains_rule_metadata(self):
        rule = _make_rule(
            name="Test Rule",
            action="escalate",
            severity="critical",
            channels=["sms", "push"],
        )
        engine = _make_engine(rules=[rule])
        triggers = await engine.evaluate("patient-1", "critical", "symptoms")
        assert len(triggers) == 1
        t = triggers[0]
        assert t.rule_name == "Test Rule"
        assert t.action == PolicyAction.ESCALATE
        assert t.severity == "critical"
        assert t.channels == ["sms", "push"]
        assert t.rule_id == str(rule["_id"])


# ── Seed Default Policies ───────────────────────────────────────────────


class TestSeedDefaultPolicies:
    """Tests for policy seeding."""

    @pytest.mark.asyncio
    async def test_seed_when_empty(self):
        engine = _make_engine(rules=[])
        count = await engine.seed_default_policies()
        assert count == 5  # 5 default rules

    @pytest.mark.asyncio
    async def test_skip_seed_when_rules_exist(self):
        engine = _make_engine(rules=[_make_rule()])
        count = await engine.seed_default_policies()
        assert count == 0
