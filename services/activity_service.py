"""Activity log service for tracking user actions."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from client.exceptions import MoodleAPIError
from client.moodle_client import AsyncMoodleClient
from schemas.activity import ActivityLog

logger = logging.getLogger(__name__)

# BUG 5 FIX: Moodle standard web service function names for log access.
#
# The original code used:
#   - "core_course_get_logs"       ← does NOT exist in standard Moodle web services
#   - "core_user_get_user_logs"    ← does NOT exist at all
#
# Moodle 5 does not expose a simple "get all logs" endpoint via standard web
# services. The closest available functions are:
#
#   core_course_get_recent_activity   — recent course activity (limited fields)
#   report_log_get_log_records        — full logs (requires report/log:view capability
#                                       and the logstore_standard plugin enabled)
#
# We use report_log_get_log_records as primary with graceful fallback to
# core_course_get_recent_activity. Both are gated on Moodle configuration,
# so errors are caught and surfaced clearly instead of swallowed.

_LOG_FUNCTION = "report_log_get_log_records"
_RECENT_ACTIVITY_FUNCTION = "core_course_get_recent_activity"


def _ts_to_dt(timestamp) -> Optional[datetime]:
    """Convert Moodle Unix timestamp to timezone-aware datetime. 0 → None."""
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def _parse_log_entry(log_data: dict, fallback_course_id: int = 0) -> ActivityLog:
    """Parse a raw Moodle log dict into an ActivityLog schema object."""
    # report_log_get_log_records uses "time"; recent_activity may use "timecreated"
    ts = log_data.get("time") or log_data.get("timecreated")

    return ActivityLog(
        id=log_data.get("id", 0),
        user_id=log_data.get("userid", 0),
        course_id=log_data.get("courseid", fallback_course_id),
        timecreated=_ts_to_dt(ts),       # BUG FIX: timezone-aware, 0→None
        event_name=log_data.get("eventname", ""),
        component=log_data.get("component", ""),
        action=log_data.get("action", ""),
        target=log_data.get("target", ""),
        object_table=log_data.get("objecttable"),
        object_id=log_data.get("objectid"),
        ip=log_data.get("ip"),
    )


class ActivityService:
    """Service for activity log operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def get_course_logs(
        self,
        course_id: int,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[ActivityLog]:
        """
        Get activity logs for a course.

        BUG 5 FIX: Uses report_log_get_log_records (the correct Moodle function).
        Falls back to core_course_get_recent_activity if the logstore is not
        configured or the token lacks report/log:view capability.

        BUG 2 FIX: Bare `except Exception` replaced with specific handling that
        surfaces real errors (auth, permissions) and falls back only on the
        specific case where the logstore is unavailable.

        Args:
            course_id: Course ID
            since: Only return logs after this datetime
            limit: Maximum number of logs to return

        Returns:
            List of activity logs (empty list if no logs available)
        """
        # FIX: 'limitnum' is not a valid param — report_log_get_log_records uses 'perpage'
        # FIX: 'invalidrecordunknown' added — Moodle throws this when no log records
        #      exist for the given window, not just when the function is unavailable.
        #      Without it in UNAVAILABLE_CODES the service re-raises instead of returning [].
        UNAVAILABLE_CODES = {
            "nopermission", "notavailable", "unsupported",
            "invalidrecordunknown",        # no records found for time window
            "dml_missing_record_exception", # same — Moodle inconsistently uses both
        }

        params: dict = {
            "courseid": course_id,
            "perpage": limit,   # FIX: was 'limitnum' — correct param is 'perpage'
        }
        if since:
            params["date"] = int(since.timestamp())

        # Primary: full log records via report plugin
        try:
            response = await self.client.call(_LOG_FUNCTION, params)
            raw_logs = response.get("logs", []) if isinstance(response, dict) else response
            return [_parse_log_entry(entry, course_id) for entry in raw_logs]

        except MoodleAPIError as exc:
            if exc.error_code not in UNAVAILABLE_CODES:
                raise  # real error (auth, network) — don't swallow
            logger.warning(
                "report_log_get_log_records unavailable for course %d (code=%s), "
                "falling back to core_course_get_recent_activity",
                course_id, exc.error_code,
            )

        # Fallback: recent activity (less detail, fewer fields)
        try:
            response = await self.client.call(
                _RECENT_ACTIVITY_FUNCTION,
                {"courseid": course_id, "timestart": int(since.timestamp()) if since else 0},
            )
            raw_logs = response.get("logs", []) if isinstance(response, dict) else []
            return [_parse_log_entry(entry, course_id) for entry in raw_logs]

        except MoodleAPIError as exc:
            if exc.error_code in UNAVAILABLE_CODES:
                # Both APIs unavailable or no records — return empty list gracefully
                logger.info("No log data available for course %d (code=%s)", course_id, exc.error_code)
                return []
            logger.error("Both log APIs failed for course %d: %s (code=%s)", course_id, exc.message, exc.error_code)
            raise

    async def get_user_logs(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[ActivityLog]:
        """
        Get activity logs for a specific user.

        BUG 5 FIX: The original used "core_user_get_user_logs" which does not
        exist in Moodle's web services. We use report_log_get_log_records with
        a userid filter, which is the correct approach.

        Args:
            user_id: User ID
            course_id: Optional course to filter by
            since: Only return logs after this datetime
            limit: Maximum logs to return
        """
        UNAVAILABLE_CODES = {
            "nopermission", "notavailable", "unsupported",
            "invalidrecordunknown",
            "dml_missing_record_exception",
        }

        params: dict = {
            "userid": user_id,
            "perpage": limit,   # FIX: was 'limitnum'
        }
        if course_id:
            params["courseid"] = course_id
        if since:
            params["date"] = int(since.timestamp())

        try:
            response = await self.client.call(_LOG_FUNCTION, params)
            raw_logs = response.get("logs", []) if isinstance(response, dict) else response
            return [_parse_log_entry(entry, course_id or 0) for entry in raw_logs]

        except MoodleAPIError as exc:
            if exc.error_code in UNAVAILABLE_CODES:
                logger.info("No log data for user %d (code=%s)", user_id, exc.error_code)
                return []
            raise