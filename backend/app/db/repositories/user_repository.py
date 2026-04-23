"""
User repository for authentication and user management.

Extends BaseRepository with user-specific operations:
- find_by_email: Lookup for login
- create_user: Insert with password hashing
"""

from typing import Any

import structlog
from bson import ObjectId

from app.db.client import AsyncMongoClient
from app.db.repositories import BaseRepository

logger = structlog.get_logger(__name__)


class UserRepository(BaseRepository):
    """Repository for user documents in the 'users' collection."""

    def __init__(self, db_client: AsyncMongoClient) -> None:
        super().__init__(db_client, "users")

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        """Find a user by email address.

        Args:
            email: The email to search for (case-insensitive).

        Returns:
            The user document dict, or None if not found.
        """
        return await self._collection.find_one(
            {"email": email.lower()}
        )

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new user with normalized email.

        Args:
            user_data: User fields including hashed_password.

        Returns:
            The created user document with _id.
        """
        user_data["email"] = user_data["email"].lower()
        return await self.create(user_data)

    async def update_user(self, user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        """Update user fields.

        Args:
            user_id: The user's ObjectId string.
            update_data: Fields to update.

        Returns:
            The updated user document.
        """
        return await self.update(user_id, update_data)

    async def deactivate_user(self, user_id: str) -> dict[str, Any]:
        """Deactivate a user account.

        Args:
            user_id: The user's ObjectId string.

        Returns:
            The updated user document.
        """
        return await self.update(user_id, {"is_active": False})
