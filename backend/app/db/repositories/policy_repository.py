"""
Policy rule data access repository.

Extends BaseRepository with active-rule queries and version management
for the risk policy engine.
"""

from typing import Any

from app.db.client import AsyncMongoClient
from app.db.repositories import BaseRepository


class PolicyRepository(BaseRepository):
    """Repository for policy rule documents in the ``policy_rules`` collection."""

    COLLECTION = "policy_rules"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        super().__init__(db_client, self.COLLECTION)

    async def get_active_rules(self) -> list[dict[str, Any]]:
        """Return all enabled (active) policy rules.

        Returns:
            List of policy rule documents.
        """
        cursor = self._collection.find({"enabled": True}).sort("risk_level", -1)
        return await cursor.to_list(length=100)

    async def get_by_risk_level(
        self,
        risk_level: str,
        enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Find policy rules matching a specific risk level.

        Args:
            risk_level: The risk level to filter by.
            enabled_only: If True, return only enabled rules.

        Returns:
            List of matching policy rule documents.
        """
        query: dict[str, Any] = {"risk_level": risk_level}
        if enabled_only:
            query["enabled"] = True
        cursor = self._collection.find(query)
        return await cursor.to_list(length=100)

    async def upsert_rule(
        self, name: str, rule_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new rule or increment version of existing rule.

        If a rule with the given name exists, its version is incremented
        and fields are updated. Otherwise, a new rule is created.

        Args:
            name: The rule name (used as lookup key).
            rule_data: Fields to set on the rule.

        Returns:
            The created or updated rule document.
        """
        existing = await self._collection.find_one({"name": name})
        if existing is not None:
            new_version = existing.get("version", 1) + 1
            rule_data["version"] = new_version
            return await self.update(str(existing["_id"]), rule_data)
        else:
            rule_data.setdefault("name", name)
            rule_data.setdefault("version", 1)
            return await self.create(rule_data)
