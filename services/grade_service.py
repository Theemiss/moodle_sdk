"""Grade management service."""

import asyncio
import logging
import re
from typing import List, Optional

from client.exceptions import MoodleNotFoundError
from client.moodle_client import AsyncMoodleClient
from schemas.grade import GradeItem, GradeReport, StudentGrade

logger = logging.getLogger(__name__)


def _parse_percentage(value) -> Optional[float]:
    """
    BUG 3 FIX: Moodle returns percentages as formatted strings, not floats.

    gradereport_user_get_grades_table returns:
        "percentageformatted": "75.00 %"   ← string with trailing space and %

    The original code stored this string directly in the schema's `percentage`
    field and later tried to format it as a float in the CLI:
        f"{grade.percentage:.1f}%"
        → ValueError: Unknown format code 'f' for object of type 'str'

    This function strips the % sign and whitespace and converts to float safely.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Strip "75.00 %" → "75.00"
        cleaned = re.sub(r"[%\s]", "", value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert Moodle grade values (may be string, None, or number)."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class GradeService:
    """Service for grade operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def get_user_grades(self, user_id: int, course_id: int) -> GradeReport:
        """
        Get grade report for a specific user in a course.

        Uses gradereport_user_get_grades_table. The response structure is
        deeply nested and varies between Moodle versions — parsing is defensive.
        """
        # Fetch user info and grades concurrently
        user_response, grade_response = await asyncio.gather(
            self.client.call(
                "core_user_get_users_by_field",
                {"field": "id", "values": [user_id]},
            ),
            self.client.call(
                "gradereport_user_get_grades_table",
                {"courseid": course_id, "userid": user_id},
            ),
        )

        if not user_response:
            raise MoodleNotFoundError("core_user_get_users_by_field", "User", user_id)

        user = user_response[0]
        grade_items = []
        student_grades = []

        tables = grade_response.get("tables", []) if isinstance(grade_response, dict) else []
        if tables:
            for item in tables[0].get("tabledata", []):
                # Skip rows without a grade object or that are pure category headers
                grade_obj = item.get("grade")
                if not isinstance(grade_obj, dict):
                    continue

                # BUG 3 FIX: use _safe_float for all numeric grade fields
                grade_item = GradeItem(
                    id=item.get("itemid", 0),
                    itemname=item.get("itemname", {}).get("content", "") if isinstance(item.get("itemname"), dict) else item.get("itemname", ""),
                    itemtype=item.get("itemtype", ""),
                    grademax=_safe_float(grade_obj.get("max")),
                    grademin=_safe_float(grade_obj.get("min")),
                    gradepass=_safe_float(grade_obj.get("pass")),
                    hidden=bool(item.get("hidden", False)),
                    locked=bool(item.get("locked", False)),
                )
                grade_items.append(grade_item)

                student_grades.append(
                    StudentGrade(
                        user_id=user_id,
                        grade_item_id=grade_item.id,
                        rawgrade=_safe_float(grade_obj.get("rawgrade")) if grade_obj.get("rawgrade") is not None else None,
                        grade=_safe_float(grade_obj.get("grade")) if grade_obj.get("grade") is not None else None,
                        percentage=_parse_percentage(grade_obj.get("percentageformatted")),  # BUG 3 FIX
                        lettergrade=grade_obj.get("lettergrade"),
                        feedback=item.get("feedback", {}).get("content") if isinstance(item.get("feedback"), dict) else None,
                        overridden=bool(item.get("overridden", False)),
                    )
                )

        return GradeReport(
            course_id=course_id,
            user_id=user_id,
            user_fullname=f"{user.get('firstname', '')} {user.get('lastname', '')}".strip(),
            grade_items=grade_items,
            grades=student_grades,
            total_grade=None,  # Computed by analytics layer if needed
        )

    async def get_course_grades(self, course_id: int) -> List[GradeReport]:
        """
        Get grade reports for all enrolled users in a course.

        BUG 7 FIX: The original used a sequential for-loop:
            for user in users:
                report = await self.get_user_grades(user.id, course_id)

        For a course with N enrolled users this makes N sequential round trips.
        With asyncio.gather all grade fetches run concurrently.
        One failed user's grades won't abort the rest (return_exceptions=True).
        """
        from services.enrollment_service import EnrollmentService

        users = await EnrollmentService(self.client).list_enrolled_users(course_id)

        if not users:
            return []

        results = await asyncio.gather(
            *[self.get_user_grades(user.id, course_id) for user in users],
            return_exceptions=True,
        )

        reports = []
        for user, result in zip(users, results):
            if isinstance(result, Exception):
                logger.warning("Failed to get grades for user %d: %s", user.id, result)
            else:
                reports.append(result)

        return reports

    async def get_grade_item(self, course_id: int, item_name: str) -> Optional[GradeItem]:
        """
        Find a grade item by name using the first enrolled user's grade report.

        Returns the first grade item whose name contains item_name (case-insensitive).
        """
        users_raw = await self.client.call(
            "core_enrol_get_enrolled_users",
            {"courseid": course_id},
        )
        if not users_raw:
            return None

        try:
            report = await self.get_user_grades(users_raw[0]["id"], course_id)
        except Exception as exc:
            logger.warning("Could not fetch grade structure for course %d: %s", course_id, exc)
            return None

        for item in report.grade_items:
            if item.itemname and item_name.lower() in item.itemname.lower():
                return item

        return None