"""
Unit tests for db/client.py — AsyncMongoClient abstraction.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure

from app.core.config import Settings


# Minimal valid environment for Settings
VALID_ENV = {
    "GEMINI_API_KEY": "test-key",
    "MONGODB_URI": "mongodb://localhost:27017",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "medgemma:4b",
}


def _make_settings() -> Settings:
    """Create a Settings instance with test values."""
    with patch.dict(os.environ, VALID_ENV, clear=False):
        return Settings()  # type: ignore[call-arg]


class TestAsyncMongoClient:
    """Tests for the AsyncMongoClient wrapper."""

    def test_initial_state_not_connected(self) -> None:
        """Client should not be connected after construction."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """connect() should establish connection on successful ping."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(return_value={"ok": 1.0})

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            await client.connect()

        assert client.is_connected is True
        mock_motor.admin.command.assert_awaited_once_with("ping")

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """connect() should raise and stay disconnected on failure."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(
            side_effect=ConnectionFailure("Connection refused")
        )

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            with pytest.raises(ConnectionFailure):
                await client.connect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """disconnect() should close connection and reset state."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(return_value={"ok": 1.0})

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            await client.connect()
            assert client.is_connected is True

            await client.disconnect()
            assert client.is_connected is False
            mock_motor.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        """disconnect() should be safe to call when not connected."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)
        await client.disconnect()  # Should not raise
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_ping_when_connected(self) -> None:
        """ping() should return ping result when connected."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(return_value={"ok": 1.0})

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            await client.connect()
            result = await client.ping()

        assert result == {"ok": 1.0}

    @pytest.mark.asyncio
    async def test_ping_when_not_connected_raises(self) -> None:
        """ping() should raise RuntimeError when not connected."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        with pytest.raises(RuntimeError, match="not connected"):
            await client.ping()

    def test_get_database_when_not_connected_raises(self) -> None:
        """get_database() should raise RuntimeError when not connected."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        with pytest.raises(RuntimeError, match="not connected"):
            client.get_database()

    @pytest.mark.asyncio
    async def test_get_database_default_name(self) -> None:
        """get_database() should use MONGODB_DB_NAME from settings by default."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(return_value={"ok": 1.0})
        mock_db = MagicMock()
        mock_motor.__getitem__ = MagicMock(return_value=mock_db)

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            await client.connect()
            db = client.get_database()

        mock_motor.__getitem__.assert_called_with("ai_medical")
        assert db is mock_db

    @pytest.mark.asyncio
    async def test_get_database_custom_name(self) -> None:
        """get_database() should accept a custom database name."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(return_value={"ok": 1.0})
        mock_db = MagicMock()
        mock_motor.__getitem__ = MagicMock(return_value=mock_db)

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            await client.connect()
            db = client.get_database("custom_db")

        mock_motor.__getitem__.assert_called_with("custom_db")

    @pytest.mark.asyncio
    async def test_get_collection(self) -> None:
        """get_collection() should return a collection from the database."""
        from app.db.client import AsyncMongoClient

        settings = _make_settings()
        client = AsyncMongoClient(settings)

        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_motor = MagicMock()
        mock_motor.admin.command = AsyncMock(return_value={"ok": 1.0})
        mock_motor.__getitem__ = MagicMock(return_value=mock_db)

        with patch("app.db.client.AsyncIOMotorClient", return_value=mock_motor):
            await client.connect()
            collection = client.get_collection("patients")

        mock_db.__getitem__.assert_called_with("patients")
        assert collection is mock_collection
