"""Core HTTP client for Moodle REST API."""

import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

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


class MoodleClient:
    """Synchronous Moodle API client."""

    def __init__(self) -> None:
        self.base_url = settings.moodle_url.rstrip("/")
        self.token = settings.moodle_token
        self.timeout = settings.request_timeout
        self._client = httpx.Client(timeout=self.timeout)

    def _build_url(self) -> str:
        """Build the Moodle webservice endpoint URL."""
        return urljoin(self.base_url, "/webservice/rest/server.php")

    def _detect_error(self, response_data: Union[Dict, List], wsfunction: str) -> None:
        """Detect and raise Moodle API errors."""
        if isinstance(response_data, dict):
            if "exception" in response_data:
                exception = response_data.get("exception", "")
                message = response_data.get("message", "")
                error_code = response_data.get("errorcode", "")
                debuginfo = response_data.get("debuginfo", "")

                # Log the full error for debugging
                logger.error(f"Moodle API Error: {exception} - {message} (code: {error_code})")
                if debuginfo:
                    logger.debug(f"Debug info: {debuginfo}")

                if error_code == "invalidtoken":
                    raise MoodleAuthError(wsfunction, message)
                elif "permission" in error_code.lower():
                    raise MoodlePermissionError(wsfunction, message)
                elif "notfound" in error_code.lower() or "invalidparameter" in error_code:
                    # Try to extract the resource ID from the message
                    import re
                    match = re.search(r'id=(\d+)', message)
                    resource_id = match.group(1) if match else "unknown"
                    raise MoodleNotFoundError(wsfunction, "resource", resource_id)
                else:
                    raise MoodleAPIError(wsfunction, exception, message, error_code)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_backoff_factor),
        reraise=True,
    )
    def call(self, wsfunction: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict, List]:
        """
        Call a Moodle web service function.

        Args:
            wsfunction: Moodle web service function name
            params: Function parameters

        Returns:
            Parsed JSON response from Moodle

        Raises:
            MoodleConnectionError: On network issues
            MoodleAPIError: On Moodle error responses
        """
        params = params or {}

        # Add required parameters
        request_params = {
            "wstoken": self.token,
            "moodlewsrestformat": "json",
            "wsfunction": wsfunction,
            **params,
        }

        url = self._build_url()

        try:
            logger.debug(
                "Calling Moodle API",
                extra={
                    "wsfunction": wsfunction,
                    "params": params,
                    "url": url,
                },
            )

            response = self._client.post(url, data=request_params)
            response.raise_for_status()
            response_data = response.json()

            self._detect_error(response_data, wsfunction)

            logger.debug(
                "Moodle API call successful",
                extra={
                    "wsfunction": wsfunction,
                    "response_size": len(str(response_data)),
                },
            )

            return response_data

        except httpx.TimeoutException as e:
            raise MoodleConnectionError(f"Request timeout for {wsfunction}", e)
        except httpx.NetworkError as e:
            raise MoodleConnectionError(f"Network error for {wsfunction}", e)
        except httpx.HTTPStatusError as e:
            raise MoodleConnectionError(f"HTTP error {e.response.status_code}", e)
        except ValueError as e:
            raise MoodleAPIError(
                wsfunction,
                "JSONDecodeError",
                f"Invalid JSON response: {e}",
                "invalidresponse",
            )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "MoodleClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()


class AsyncMoodleClient:
    """Asynchronous Moodle API client."""

    def __init__(self) -> None:
        self.base_url = settings.moodle_url.rstrip("/")
        self.token = settings.moodle_token
        self.timeout = settings.request_timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    def _build_url(self) -> str:
        """Build the Moodle webservice endpoint URL."""
        return urljoin(self.base_url, "/webservice/rest/server.php")

    def _detect_error(self, response_data: Union[Dict, List], wsfunction: str) -> None:
        """Detect and raise Moodle API errors."""
        if isinstance(response_data, dict):
            if "exception" in response_data:
                exception = response_data.get("exception", "")
                message = response_data.get("message", "")
                error_code = response_data.get("errorcode", "")

                if error_code == "invalidtoken":
                    raise MoodleAuthError(wsfunction, message)
                elif "permission" in error_code.lower():
                    raise MoodlePermissionError(wsfunction, message)
                elif "notfound" in error_code.lower() or "invalidparameter" in error_code:
                    raise MoodleNotFoundError(wsfunction, "resource", "unknown")
                else:
                    raise MoodleAPIError(wsfunction, exception, message, error_code)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_backoff_factor),
        reraise=True,
    )
    async def call(self, wsfunction: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict, List]:
        """
        Call a Moodle web service function asynchronously.

        Args:
            wsfunction: Moodle web service function name
            params: Function parameters

        Returns:
            Parsed JSON response from Moodle

        Raises:
            MoodleConnectionError: On network issues
            MoodleAPIError: On Moodle error responses
        """
        params = params or {}

        request_params = {
            "wstoken": self.token,
            "moodlewsrestformat": "json",
            "wsfunction": wsfunction,
            **params,
        }

        url = self._build_url()

        try:
            logger.debug(
                "Calling Moodle API (async)",
                extra={
                    "wsfunction": wsfunction,
                    "params": params,
                    "url": url,
                },
            )

            response = await self._client.post(url, data=request_params)
            response.raise_for_status()
            response_data = response.json()

            self._detect_error(response_data, wsfunction)

            logger.debug(
                "Moodle API call successful (async)",
                extra={
                    "wsfunction": wsfunction,
                    "response_size": len(str(response_data)),
                },
            )

            return response_data

        except httpx.TimeoutException as e:
            raise MoodleConnectionError(f"Request timeout for {wsfunction}", e)
        except httpx.NetworkError as e:
            raise MoodleConnectionError(f"Network error for {wsfunction}", e)
        except httpx.HTTPStatusError as e:
            raise MoodleConnectionError(f"HTTP error {e.response.status_code}", e)
        except ValueError as e:
            raise MoodleAPIError(
                wsfunction,
                "JSONDecodeError",
                f"Invalid JSON response: {e}",
                "invalidresponse",
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncMoodleClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()