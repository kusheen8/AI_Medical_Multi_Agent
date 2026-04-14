"""
Async MongoDB client abstraction.

Wraps the Motor async driver behind an abstraction layer so that
dependent code does not directly import Motor. This enables a
future migration to PyMongo's native async driver (Motor is
deprecated, removal scheduled May 14 2026).

Usage:
    client = AsyncMongoClient(settings)
    await client.connect()
    db = client.get_database()
    collection = client.get_collection("patients")
    await client.disconnect()
"""

from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import Settings

logger = structlog.get_logger(__name__)


class AsyncMongoClient:
    """Async MongoDB client with connection lifecycle management.

    Provides an abstraction layer over Motor to isolate driver-specific
    code. When migrating to PyMongo async, only this module needs changes.

    Attributes:
        _client: The underlying Motor client instance (None until connect()).
        _settings: Application settings for connection configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        """Establish connection to MongoDB with configured pool settings.

        Raises:
            ConnectionFailure: If the initial connection attempt fails.
        """
        await logger.ainfo(
            "mongodb_connecting",
            db_name=self._settings.MONGODB_DB_NAME,
            min_pool=self._settings.MONGODB_MIN_POOL_SIZE,
            max_pool=self._settings.MONGODB_MAX_POOL_SIZE,
        )

        try:
            self._client = AsyncIOMotorClient(
                self._settings.MONGODB_URI,
                minPoolSize=self._settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=self._settings.MONGODB_MAX_POOL_SIZE,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            # Verify connectivity with a ping
            await self._client.admin.command("ping")
            await logger.ainfo("mongodb_connected")
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            await logger.aerror("mongodb_connection_failed", error=str(exc))
            self._client = None
            raise

    async def disconnect(self) -> None:
        """Close the MongoDB connection and release pool resources."""
        if self._client is not None:
            self._client.close()
            self._client = None
            await logger.ainfo("mongodb_disconnected")

    async def ping(self) -> dict[str, Any]:
        """Ping MongoDB to verify connectivity.

        Returns:
            dict with 'ok' key (1.0 if healthy).

        Raises:
            ConnectionFailure: If the ping fails.
            RuntimeError: If the client is not connected.
        """
        if self._client is None:
            raise RuntimeError("MongoDB client is not connected. Call connect() first.")
        return await self._client.admin.command("ping")

    def get_database(self, name: str | None = None) -> Any:
        """Get a database instance.

        Args:
            name: Database name. Defaults to MONGODB_DB_NAME from settings.

        Returns:
            AsyncIOMotorDatabase instance.

        Raises:
            RuntimeError: If the client is not connected.
        """
        if self._client is None:
            raise RuntimeError("MongoDB client is not connected. Call connect() first.")
        db_name = name or self._settings.MONGODB_DB_NAME
        return self._client[db_name]

    def get_collection(
        self, collection_name: str, db_name: str | None = None
    ) -> Any:
        """Get a collection from the specified database.

        Args:
            collection_name: Name of the collection.
            db_name: Database name. Defaults to MONGODB_DB_NAME from settings.

        Returns:
            AsyncIOMotorCollection instance.
        """
        db = self.get_database(db_name)
        return db[collection_name]

    @property
    def is_connected(self) -> bool:
        """Check if the client has an active connection."""
        return self._client is not None
