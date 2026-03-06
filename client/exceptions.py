"""Exception hierarchy for the Moodle backend."""

from typing import Any, Optional


class MoodleBackendError(Exception):
    """Base exception for all Moodle backend errors."""

    def __init__(self, message: str, *args: Any) -> None:
        self.message = message
        super().__init__(message, *args)


class MoodleAPIError(MoodleBackendError):
    """Moodle API returned an error response."""

    def __init__(
        self,
        function: str,
        exception: str,
        message: str,
        error_code: str,
        *args: Any,
    ) -> None:
        self.function = function
        self.exception = exception
        self.error_code = error_code
        full_message = f"[{function}] {exception}: {message} (code: {error_code})"
        super().__init__(full_message, *args)


class MoodleAuthError(MoodleAPIError):
    """Authentication failed (invalid/expired token)."""

    def __init__(self, function: str, message: str, *args: Any) -> None:
        super().__init__(
            function=function,
            exception="AuthError",
            message=message,
            error_code="invalidtoken",
            *args,
        )


class MoodleNotFoundError(MoodleAPIError):
    """Resource not found."""

    def __init__(self, function: str, resource_type: str, resource_id: Any, *args: Any) -> None:
        super().__init__(
            function=function,
            exception="NotFoundError",
            message=f"{resource_type} with identifier {resource_id} not found",
            error_code="notfound",
            *args,
        )


class MoodlePermissionError(MoodleAPIError):
    """Insufficient permissions to perform operation."""

    def __init__(self, function: str, message: str, *args: Any) -> None:
        super().__init__(
            function=function,
            exception="PermissionError",
            message=message,
            error_code="permissiondenied",
            *args,
        )


class MoodleConnectionError(MoodleBackendError):
    """Network or connection-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        self.original_error = original_error
        super().__init__(message)


class MoodleValidationError(MoodleBackendError):
    """Input validation error before API call."""

    def __init__(self, field: str, message: str, *args: Any) -> None:
        self.field = field
        super().__init__(f"Validation error on {field}: {message}", *args)


class BulkOperationError(MoodleBackendError):
    """Partial failure in bulk operations."""

    def __init__(
        self,
        message: str,
        succeeded: list[int],
        failed: list[tuple[int, str]],
        *args: Any,
    ) -> None:
        self.succeeded = succeeded
        self.failed = failed
        success_count = len(succeeded)
        fail_count = len(failed)
        super().__init__(
            f"{message}: {success_count} succeeded, {fail_count} failed",
            *args,
        )