"""Enrollment management service."""

import asyncio
import logging
from typing import List, Optional, Set, Tuple

from client.exceptions import MoodleNotFoundError, BulkOperationError
from client.moodle_client import AsyncMoodleClient
from config.settings import settings
from schemas.course import Course
from schemas.enrollment import (
    BulkEnrollRequest,
    BulkEnrollResult,
    EnrollmentRequest,
    EnrolledUser,
    SyncResult,
)

logger = logging.getLogger(__name__)


class EnrollmentService:
    """Service for enrollment operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client
        self.bulk_chunk_size = settings.bulk_chunk_size

    async def enroll_user(self, user_id: int, course_id: int, role_id: int = 5) -> bool:
        """
        Enroll a single user in a course.

        Args:
            user_id: User ID
            course_id: Course ID
            role_id: Role ID (5 = student, 3 = teacher, etc.)

        Returns:
            True if successful
        """
        params = {
            "enrolments": [
                {
                    "roleid": role_id,
                    "userid": user_id,
                    "courseid": course_id,
                }
            ]
        }

        response = await self.client.call("enrol_manual_enrol_users", params)
        return True

    async def unenroll_user(self, user_id: int, course_id: int) -> bool:
        """
        Unenroll a user from a course.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            True if successful
        """
        params = {
            "enrolments": [
                {
                    "userid": user_id,
                    "courseid": course_id,
                }
            ]
        }

        response = await self.client.call("enrol_manual_unenrol_users", params)
        return True

    async def bulk_enroll(self, requests: List[EnrollmentRequest]) -> BulkEnrollResult:
        """
        Bulk enroll multiple users in multiple courses.

        Args:
            requests: List of enrollment requests

        Returns:
            Bulk enroll result with success/failure counts
        """
        succeeded = 0
        failed = 0
        failures = []

        # Process in chunks to avoid request size limits
        for i in range(0, len(requests), self.bulk_chunk_size):
            chunk = requests[i : i + self.bulk_chunk_size]
            chunk_enrolments = []

            for req in chunk:
                chunk_enrolments.append(
                    {
                        "roleid": req.role_id,
                        "userid": req.user_id,
                        "courseid": req.course_id,
                        "timestart": int(req.timestart.timestamp()) if req.timestart else 0,
                        "timeend": int(req.timeend.timestamp()) if req.timeend else 0,
                    }
                )

            try:
                params = {"enrolments": chunk_enrolments}
                await self.client.call("enrol_manual_enrol_users", params)
                succeeded += len(chunk)
            except Exception as e:
                # If whole chunk fails, record individual failures
                failed += len(chunk)
                for req in chunk:
                    failures.append((req.user_id, req.course_id, str(e)))

            # Small delay between chunks
            await asyncio.sleep(0.2)

        return BulkEnrollResult(
            total=len(requests),
            succeeded=succeeded,
            failed=failed,
            failures=failures,
        )

    async def list_enrolled_users(self, course_id: int) -> List[EnrolledUser]:
        """
        List all users enrolled in a course.

        Args:
            course_id: Course ID

        Returns:
            List of enrolled users with their roles
        """
        params = {"courseid": course_id, "options": [{"name": "withcapability", "value": "moodle/course:view"}]}

        response = await self.client.call("core_enrol_get_enrolled_users", params)

        users = []
        for user_data in response:
            roles = [role["shortname"] for role in user_data.get("roles", [])]
            groups = [group["name"] for group in user_data.get("groups", [])]

            users.append(
                EnrolledUser(
                    id=user_data["id"],
                    username=user_data["username"],
                    firstname=user_data["firstname"],
                    lastname=user_data["lastname"],
                    fullname=user_data["fullname"],
                    email=user_data["email"],
                    roles=roles,
                    groups=groups,
                )
            )

        return users

    async def sync_enrollments(self, course_id: int, expected: List[EnrollmentRequest]) -> SyncResult:
        """
        Sync enrollments to match expected state.

        Args:
            course_id: Course ID
            expected: List of expected enrollments

        Returns:
            Sync result with counts of added/removed users
        """
        # Get current enrollments
        current_users = await self.list_enrolled_users(course_id)
        current_set = {(u.id, 5)}  # TODO: Handle multiple roles properly

        # Build expected set
        expected_set = {(req.user_id, req.role_id) for req in expected}

        # Find differences
        to_remove = current_set - expected_set
        to_add = expected_set - current_set

        added = 0
        removed = 0
        errors = []

        # Remove users
        for user_id, role_id in to_remove:
            try:
                await self.unenroll_user(user_id, course_id)
                removed += 1
            except Exception as e:
                errors.append(f"Failed to unenroll user {user_id}: {e}")

        # Add users
        for user_id, role_id in to_add:
            try:
                await self.enroll_user(user_id, course_id, role_id)
                added += 1
            except Exception as e:
                errors.append(f"Failed to enroll user {user_id}: {e}")

        return SyncResult(
            course_id=course_id,
            expected_count=len(expected_set),
            actual_count=len(current_set) - removed + added,
            added=added,
            removed=removed,
            unchanged=len(current_set & expected_set),
            errors=errors,
        )

    async def get_user_enrollments(self, user_id: int) -> List[Course]:
        """
        Get all courses a user is enrolled in.

        Args:
            user_id: User ID

        Returns:
            List of courses
        """
        params = {"userid": user_id}
        response = await self.client.call("core_enrol_get_users_courses", params)

        courses = []
        for course_data in response:
            from schemas.course import Course
            from utils.transformers import transform_course

            courses.append(transform_course(course_data))

        return courses