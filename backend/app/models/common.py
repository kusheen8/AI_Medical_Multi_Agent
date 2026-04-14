"""
Common model utilities shared across all domain models.

Provides:
- PyObjectId: Custom type for MongoDB ObjectId ↔ str serialization
- TimestampMixin: Auto-managed created_at / updated_at fields
- PaginatedResponse: Generic paginated list wrapper
- ErrorDetail: Structured validation error response schema
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from bson import ObjectId
from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class PyObjectId(ObjectId):
    """Custom ObjectId type that integrates with Pydantic v2 serialization.

    Accepts both ``str`` and ``ObjectId`` on input; always serializes to ``str``
    in JSON responses.  Used as the ``id`` field type on all DB models.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def validate(cls, value: Any) -> "PyObjectId":
        if isinstance(value, ObjectId):
            return cls(str(value))
        if isinstance(value, str) and ObjectId.is_valid(value):
            return cls(value)
        raise ValueError(f"Invalid ObjectId: {value!r}")


class TimestampMixin(BaseModel):
    """Mixin providing automatic timestamp fields.

    ``created_at`` defaults to now; ``updated_at`` defaults to now and should
    be refreshed on every write.
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the record was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the record was last updated.",
    )


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response.

    Attributes:
        items: List of results for the current page.
        total: Total number of matching documents.
        page: Current page number (1-indexed).
        page_size: Maximum items per page.
        pages: Total number of pages.
    """

    items: list[T]
    total: int = Field(ge=0, description="Total matching documents.")
    page: int = Field(ge=1, description="Current page (1-indexed).")
    page_size: int = Field(ge=1, le=100, description="Items per page.")
    pages: int = Field(ge=0, description="Total pages.")


class ErrorDetail(BaseModel):
    """Structured error response returned on validation failures (HTTP 422)."""

    detail: str = Field(description="Human-readable error summary.")
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-field validation errors.",
    )
