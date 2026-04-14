"""
Custom exception classes for the data access layer.

These exceptions are raised by repository methods and translated into
appropriate HTTP responses by the global error handlers in the API layer.
"""


class RepositoryError(Exception):
    """Base exception for all repository-level errors."""

    def __init__(self, message: str = "An unexpected repository error occurred.") -> None:
        self.message = message
        super().__init__(self.message)


class NotFoundError(RepositoryError):
    """Raised when a requested document does not exist."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} with id '{resource_id}' not found.")


class DuplicateError(RepositoryError):
    """Raised when a unique constraint is violated (e.g., idempotency key)."""

    def __init__(self, message: str = "Duplicate resource.") -> None:
        super().__init__(message)
