"""Database package — client abstraction, repositories, and exceptions."""

from app.db.client import AsyncMongoClient
from app.db.exceptions import DuplicateError, NotFoundError, RepositoryError

__all__ = [
    "AsyncMongoClient",
    "NotFoundError",
    "DuplicateError",
    "RepositoryError",
]
