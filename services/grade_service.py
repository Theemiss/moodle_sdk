"""Grade management service."""

import logging
from typing import List, Optional

from client.exceptions import MoodleNotFoundError
from client.moodle_client import AsyncMoodleClient
from schemas.grade import GradeItem, GradeReport, StudentGrade

logger = logging.getLogger(__name__)


class GradeService:
    """Service for grade operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def get_user_grades(self, user_id: int, course_id: int) -> GradeReport:
        """
        Get grade report for a specific user in a course.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            Grade report for the user
        """
        # Get user info
        user_response = await self.client.call(
            "core_user_get_users_by_field",
            {"field": "id", "values": [user_id]},
        )

        if not user_response:
            raise MoodleNotFoundError("core_user_get_users_by_field", "User", user_id)

        user = user_response[0]

        # Get grades
        params = {
            "courseid": course_id,
            "userid": user_id,
        }

        response = await self.client.call("gradereport_user_get_grades_table", params)

        grade_items = []
        student_grades = []
        total_grade = None

        if "tables" in response and len(response["tables"]) > 0:
            table = response["tables"][0]

            for item in table.get("tabledata", []):
                # Skip category headers
                if item.get("itemtype") == "category" and "leader" in item.get("class", ""):
                    continue

                grade_item = GradeItem(
                    id=item.get("itemid", 0),
                    itemname=item.get("itemname", ""),
                    itemtype=item.get("itemtype", ""),
                    grademax=float(item.get("grade", {}).get("max", 0)),
                    grademin=float(item.get("grade", {}).get("min", 0)),
                    gradepass=float(item.get("grade", {}).get("pass", 0)),
                    hidden=item.get("hidden", False),
                    locked=item.get("locked", False),
                )
                grade_items.append(grade_item)

                # Get student's grade for this item
                if "grade" in item:
                    student_grade = StudentGrade(
                        user_id=user_id,
                        grade_item_id=grade_item.id,
                        rawgrade=item["grade"].get("rawgrade"),
                        grade=item["grade"].get("grade"),
                        percentage=item["grade"].get("percentageformatted"),
                        lettergrade=item["grade"].get("lettergrade"),
                        feedback=item.get("feedback", {}).get("content"),
                        overridden=item.get("overridden", False),
                    )
                    student_grades.append(student_grade)

        return GradeReport(
            course_id=course_id,
            user_id=user_id,
            user_fullname=f"{user.get('firstname', '')} {user.get('lastname', '')}",
            grade_items=grade_items,
            grades=student_grades,
            total_grade=total_grade,
        )

    async def get_course_grades(self, course_id: int) -> List[GradeReport]:
        """
        Get grade reports for all users in a course.

        Args:
            course_id: Course ID

        Returns:
            List of grade reports
        """
        # Get enrolled users first
        from services.enrollment_service import EnrollmentService

        enrollment_service = EnrollmentService(self.client)
        users = await enrollment_service.list_enrolled_users(course_id)

        reports = []
        for user in users:
            try:
                report = await self.get_user_grades(user.id, course_id)
                reports.append(report)
            except Exception as e:
                logger.warning(f"Failed to get grades for user {user.id}: {e}")

        return reports

    async def get_grade_item(self, course_id: int, item_name: str) -> Optional[GradeItem]:
        """
        Get a specific grade item by name.

        Args:
            course_id: Course ID
            item_name: Grade item name

        Returns:
            Grade item if found, None otherwise
        """
        # Get first user's grades to see structure
        users = await self.client.call("core_enrol_get_enrolled_users", {"courseid": course_id})
        if not users:
            return None

        report = await self.get_user_grades(users[0]["id"], course_id)

        for item in report.grade_items:
            if item.itemname and item_name.lower() in item.itemname.lower():
                return item

        return None