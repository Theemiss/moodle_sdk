"""Core HTTP client for Moodle REST API."""

import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from client.exceptions import (
    MoodleAPIError,
    MoodleAuthError,
    MoodleConnectionError,
    MoodleNotFoundError,
    MoodlePermissionError,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# BUG 1 FIX: Moodle parameter serialization
#
# httpx sends nested Python dicts/lists as their string representations, e.g.:
#   courses=[{'shortname': 'test'}]
#
# Moodle 5 REST API requires PHP-style indexed form encoding:
#   courses[0][shortname]=test&courses[0][categoryid]=1
#
# This broke ALL service calls that use nested params:
#   create_course, update_course, enroll_user, list_courses w/ criteria, etc.
# ─────────────────────────────────────────────────────────────────────────────
def flatten_moodle_params(params: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """
    Recursively flatten nested dicts and lists into Moodle's PHP-indexed format.

    Examples:
        {"courses": [{"shortname": "CS101", "categoryid": 1}]}
        → {"courses[0][shortname]": "CS101", "courses[0][categoryid]": 1}

        {"criteria": [{"key": "category", "value": 5}]}
        → {"criteria[0][key]": "category", "criteria[0][value]": 5}

        {"courseids": [1, 2, 3]}
        → {"courseids[0]": 1, "courseids[1]": 2, "courseids[2]": 3}
    """
    result: Dict[str, Any] = {}
    for key, value in params.items():
        full_key = f"{prefix}[{key}]" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_moodle_params(value, full_key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                indexed_key = f"{full_key}[{i}]"
                if isinstance(item, dict):
                    result.update(flatten_moodle_params(item, indexed_key))
                else:
                    if item is not None:
                        result[indexed_key] = item
        elif value is not None:
            result[full_key] = value

    return result


def _build_endpoint_url(base_url: str) -> str:
    """
    Build Moodle webservice endpoint URL.

    BUG 2 FIX: The original code used urljoin() which silently drops subdirectory
    paths when the API path starts with '/':

        urljoin("https://example.com/moodle/", "/webservice/rest/server.php")
        → "https://example.com/webservice/rest/server.php"   ← WRONG

    Fix: use string concatenation so subdirectory installs work correctly:
        "https://example.com/moodle" + "/webservice/rest/server.php"
        → "https://example.com/moodle/webservice/rest/server.php"  ← CORRECT
    """
    return base_url.rstrip("/") + "/webservice/rest/server.php"


def _detect_moodle_error(response_data: Union[Dict, List], wsfunction: str) -> None:
    """
    Detect and raise typed exceptions from Moodle error responses.

    Moodle always returns HTTP 200, even on failures. Errors are embedded in the
    JSON body as {"exception": "...", "errorcode": "...", "message": "..."}.

    BUG 3 FIX: The original code also checked `if "error" in response_data` which
    is too broad — any valid Moodle object that happens to have an "error" key
    (e.g. from a custom field or plugin) would raise a false-positive exception.
    The correct check is ONLY for the "exception" key, which Moodle uses exclusively
    for error responses.
    """
    if not isinstance(response_data, dict):
        return  # List responses (course lists, user lists) are never errors

    if "exception" not in response_data:
        return  # No exception key → valid response

    exception = response_data.get("exception", "")
    message = response_data.get("message", "Unknown error")
    error_code = response_data.get("errorcode", "unknown")
    debuginfo = response_data.get("debuginfo", "")

    # NOTE: 'message' is a reserved Python LogRecord field — using it in extra={}
    # raises KeyError: "Attempt to overwrite 'message' in LogRecord".
    # Use 'moodle_message' instead.
    logger.error(
        "Moodle API error [%s] %s: %s (code=%s)",
        wsfunction, exception, message, error_code,
    )
    if debuginfo:
        logger.debug("Moodle debug info: %s", debuginfo)

    # Map known Moodle error codes to typed exceptions
    if error_code in ("invalidtoken", "accessexception"):
        raise MoodleAuthError(wsfunction, message)

    if "permission" in error_code.lower() or "nopermission" in error_code:
        raise MoodlePermissionError(wsfunction, message)

    if error_code in ("invalidparameter", "invalidrecord", "dml_missing_record_exception"):
        raise MoodleNotFoundError(wsfunction, "resource", "unknown")

    raise MoodleAPIError(wsfunction, exception, message, error_code)


class MoodleClient:
    """Synchronous Moodle REST API client."""

    def __init__(self) -> None:
        self.endpoint_url = _build_endpoint_url(settings.moodle_url)
        self.token = settings.moodle_token
        self._client = httpx.Client(timeout=settings.request_timeout)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_backoff_factor),
        reraise=True,
    )
    def call(
        self, wsfunction: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[Dict, List]:
        """
        Call a Moodle web service function synchronously.

        Args:
            wsfunction: Moodle web service function name (e.g. core_course_get_courses)
            params: Optional dict of parameters — nested dicts/lists are auto-flattened

        Returns:
            Parsed JSON response

        Raises:
            MoodleAuthError: Token is invalid or expired
            MoodlePermissionError: Token lacks required capabilities
            MoodleNotFoundError: Requested resource doesn't exist
            MoodleAPIError: Other Moodle-side error
            MoodleConnectionError: Network/timeout issues
        """
        base_params = {
            "wstoken": self.token,
            "moodlewsrestformat": "json",
            "wsfunction": wsfunction,
        }
        nested = flatten_moodle_params(params or {})
        request_params = {**base_params, **nested}

        logger.debug("Moodle API call → %s", wsfunction)

        try:
            response = self._client.post(self.endpoint_url, data=request_params)
            response.raise_for_status()
            data = response.json()
            _detect_moodle_error(data, wsfunction)
            return data

        except httpx.TimeoutException as exc:
            raise MoodleConnectionError(f"Timeout calling {wsfunction}", exc)
        except httpx.NetworkError as exc:
            raise MoodleConnectionError(f"Network error calling {wsfunction}", exc)
        except httpx.HTTPStatusError as exc:
            raise MoodleConnectionError(
                f"HTTP {exc.response.status_code} from Moodle ({wsfunction})", exc
            )
        except ValueError as exc:
            raise MoodleAPIError(
                wsfunction, "JSONDecodeError", f"Invalid JSON: {exc}", "invalidresponse"
            )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MoodleClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncMoodleClient:
    """Asynchronous Moodle REST API client."""

    def __init__(self) -> None:
        self.endpoint_url = _build_endpoint_url(settings.moodle_url)
        self.token = settings.moodle_token
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)

    # NOTE: tenacity's @retry decorator supports async functions natively since v8.0.
    # It detects coroutines and wraps them correctly — no AsyncRetrying needed here.
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_backoff_factor),
        reraise=True,
    )
    async def call(
        self, wsfunction: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[Dict, List]:
        """
        Call a Moodle web service function asynchronously.

        Args:
            wsfunction: Moodle web service function name
            params: Optional dict of parameters — nested dicts/lists are auto-flattened

        Returns:
            Parsed JSON response
        """
        base_params = {
            "wstoken": self.token,
            "moodlewsrestformat": "json",
            "wsfunction": wsfunction,
        }
        nested = flatten_moodle_params(params or {})
        request_params = {**base_params, **nested}

        logger.debug("Moodle API call (async) → %s", wsfunction)

        try:
            response = await self._client.post(self.endpoint_url, data=request_params)
            response.raise_for_status()
            data = response.json()
            _detect_moodle_error(data, wsfunction)
            return data

        except httpx.TimeoutException as exc:
            raise MoodleConnectionError(f"Timeout calling {wsfunction}", exc)
        except httpx.NetworkError as exc:
            raise MoodleConnectionError(f"Network error calling {wsfunction}", exc)
        except httpx.HTTPStatusError as exc:
            raise MoodleConnectionError(
                f"HTTP {exc.response.status_code} from Moodle ({wsfunction})", exc
            )
        except ValueError as exc:
            raise MoodleAPIError(
                wsfunction, "JSONDecodeError", f"Invalid JSON: {exc}", "invalidresponse"
            )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncMoodleClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()