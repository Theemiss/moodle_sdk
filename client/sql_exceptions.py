"""Exception hierarchy for SQL database operations."""

from typing import Any, Optional


class DatabaseError(Exception):
    """Base exception for all database errors."""

    def __init__(self, message: str, *args: Any) -> None:
        self.message = message
        super().__init__(message, *args)


class ConnectionError(DatabaseError):
    """Database connection errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        self.original_error = original_error
        super().__init__(f"Connection error: {message}")


class QueryError(DatabaseError):
    """SQL query execution errors."""

    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None, 
        params: Optional[dict] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        self.query = query
        self.params = params
        self.original_error = original_error
        detail = f"{message}"
        if query:
            detail += f"\nQuery: {query}"
        super().__init__(detail)


class QueryTimeoutError(QueryError):
    """Query execution timeout."""

    def __init__(self, query: Optional[str] = None, timeout: Optional[int] = None) -> None:
        message = f"Query timeout after {timeout} seconds" if timeout else "Query timeout"
        super().__init__(message, query=query)


class QueryValidationError(QueryError):
    """Query validation errors (safety checks, blocked operations)."""

    def __init__(self, message: str, query: Optional[str] = None) -> None:
        super().__init__(message, query=query)


class DataError(DatabaseError):
    """Data integrity or formatting errors."""

    def __init__(self, message: str, *args: Any) -> None:
        super().__init__(f"Data error: {message}", *args)


class TransactionError(DatabaseError):
    """Transaction management errors."""

    def __init__(self, message: str, *args: Any) -> None:
        super().__init__(f"Transaction error: {message}", *args)


class SchemaError(DatabaseError):
    """Database schema-related errors."""

    def __init__(self, message: str, *args: Any) -> None:
        super().__init__(f"Schema error: {message}", *args)


class PoolExhaustedError(DatabaseError):
    """Connection pool exhausted."""

    def __init__(self, message: str = "Connection pool exhausted", *args: Any) -> None:
        super().__init__(message, *args)