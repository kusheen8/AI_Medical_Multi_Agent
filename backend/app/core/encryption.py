"""
Application-level field encryption for PHI data at rest.

Uses Fernet symmetric encryption to encrypt sensitive fields before
MongoDB storage and decrypt on retrieval.

Features:
- Per-field encryption/decryption
- Key rotation support (multiple decryption keys, single encryption key)
- Graceful fallback for unencrypted data (migration-friendly)

Usage::

    encryptor = FieldEncryptor(key="base64-fernet-key")
    encrypted = encryptor.encrypt_field("John Doe")
    decrypted = encryptor.decrypt_field(encrypted)
"""

import structlog
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from typing import Any

logger = structlog.get_logger(__name__)

# Prefix to identify encrypted values (prevents double-encryption)
_ENCRYPTED_PREFIX = "enc::"


class FieldEncryptor:
    """Encrypts and decrypts individual field values using Fernet.

    Attributes:
        _fernet: The Fernet (or MultiFernet) instance for crypto operations.
        _enabled: Whether encryption is active (requires valid key).
    """

    def __init__(self, key: str = "", rotation_keys: list[str] | None = None) -> None:
        """Initialize the field encryptor.

        Args:
            key: Primary Fernet key (base64-encoded). Empty string disables encryption.
            rotation_keys: Optional list of older keys for decryption during rotation.
        """
        self._enabled = False
        self._fernet: Fernet | MultiFernet | None = None

        if not key:
            return

        try:
            primary = Fernet(key.encode() if isinstance(key, str) else key)
            if rotation_keys:
                old_keys = [
                    Fernet(k.encode() if isinstance(k, str) else k)
                    for k in rotation_keys
                ]
                self._fernet = MultiFernet([primary, *old_keys])
            else:
                self._fernet = primary
            self._enabled = True
        except Exception:
            logger.warning(
                "field_encryption_disabled",
                reason="Invalid encryption key provided.",
            )

    @property
    def enabled(self) -> bool:
        """Whether encryption is active."""
        return self._enabled

    def encrypt_field(self, value: str) -> str:
        """Encrypt a single field value.

        Args:
            value: The plaintext value to encrypt.

        Returns:
            The encrypted value prefixed with 'enc::',
            or the original value if encryption is disabled.
        """
        if not self._enabled or not value:
            return value

        # Don't double-encrypt
        if value.startswith(_ENCRYPTED_PREFIX):
            return value

        try:
            encrypted = self._fernet.encrypt(value.encode("utf-8"))  # type: ignore[union-attr]
            return f"{_ENCRYPTED_PREFIX}{encrypted.decode('utf-8')}"
        except Exception:
            logger.warning("field_encryption_failed", exc_info=True)
            return value

    def decrypt_field(self, value: str) -> str:
        """Decrypt a single field value.

        Args:
            value: The encrypted value (with 'enc::' prefix).

        Returns:
            The decrypted plaintext value,
            or the original value if not encrypted or decryption fails.
        """
        if not self._enabled or not value:
            return value

        # Only decrypt values with our prefix
        if not value.startswith(_ENCRYPTED_PREFIX):
            return value

        encrypted_data = value[len(_ENCRYPTED_PREFIX):]
        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode("utf-8"))  # type: ignore[union-attr]
            return decrypted.decode("utf-8")
        except InvalidToken:
            logger.warning("field_decryption_failed", reason="invalid_token")
            return value
        except Exception:
            logger.warning("field_decryption_failed", exc_info=True)
            return value

    def encrypt_document(
        self, doc: dict[str, Any], fields: list[str]
    ) -> dict[str, Any]:
        """Encrypt specified fields in a document dict.

        Args:
            doc: The document to process (modified in-place).
            fields: List of field names to encrypt.

        Returns:
            The document with encrypted fields.
        """
        if not self._enabled:
            return doc

        for field in fields:
            if field in doc and isinstance(doc[field], str):
                doc[field] = self.encrypt_field(doc[field])
            elif field in doc and isinstance(doc[field], dict):
                # Encrypt dict by serializing to JSON string
                import json
                serialized = json.dumps(doc[field], default=str)
                doc[field] = self.encrypt_field(serialized)
        return doc

    def decrypt_document(
        self, doc: dict[str, Any], fields: list[str]
    ) -> dict[str, Any]:
        """Decrypt specified fields in a document dict.

        Args:
            doc: The document to process (modified in-place).
            fields: List of field names to decrypt.

        Returns:
            The document with decrypted fields.
        """
        if not self._enabled:
            return doc

        for field in fields:
            if field in doc and isinstance(doc[field], str):
                decrypted = self.decrypt_field(doc[field])
                # Try to parse back as JSON (for dict fields)
                if decrypted.startswith("{") or decrypted.startswith("["):
                    try:
                        import json
                        doc[field] = json.loads(decrypted)
                    except (json.JSONDecodeError, ValueError):
                        doc[field] = decrypted
                else:
                    doc[field] = decrypted
        return doc


# Module-level singleton (initialized on first use)
_encryptor: FieldEncryptor | None = None


def get_field_encryptor() -> FieldEncryptor:
    """Get or create the global FieldEncryptor singleton.

    Returns:
        The configured FieldEncryptor instance.
    """
    global _encryptor
    if _encryptor is None:
        from app.core.config import get_settings
        settings = get_settings()
        _encryptor = FieldEncryptor(key=settings.FIELD_ENCRYPTION_KEY)
    return _encryptor


def reset_field_encryptor() -> None:
    """Reset the singleton (for testing)."""
    global _encryptor
    _encryptor = None
