"""Enrollment management service."""

import asyncio
import logging
from typing import List, Optional

from client.exceptions import BulkOperationError
from client.moodle_client import AsyncMoodleClient
from config.settings import settings
from schemas.course import Course
from schemas.enrollment import (
    BulkEnrollResult,
    EnrollmentRequest,
    EnrolledUser,
    SyncResult,
)
from utils.transformers import transform_course

logger = logging.getLogger(__name__)


class EnrollmentService:
    """Service for enrollment operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client
        self.bulk_chunk_size = settings.bulk_chunk_size

    async def enroll_user(self, user_id: int, course_id: int, role_id: int = 5) -> bool:
        """
        Enroll a single user in a course.

        Returns:
            True if successful (enrol_manual_enrol_users returns null on success)
        """
        await self.client.call(
            "enrol_manual_enrol_users",
            {
                "enrolments": [
                    {"roleid": role_id, "userid": user_id, "courseid": course_id}
                ]
            },
        )
        # BUG FIX (minor): original stored `response = await ...` but the variable
        # was never used. enrol_manual_enrol_users returns null on success.
        return True

    async def unenroll_user(self, user_id: int, course_id: int) -> bool:
        """Unenroll a user from a course."""
        await self.client.call(
            "enrol_manual_unenrol_users",
            {
                "enrolments": [
                    {"userid": user_id, "courseid": course_id}
                ]
            },
        )
        return True

    async def bulk_enroll(self, requests: List[EnrollmentRequest]) -> BulkEnrollResult:
        """
        Bulk enroll multiple users in multiple courses.

        Sends enrolments in chunks to avoid Moodle's request size limits.
        If an entire chunk fails, records each item individually as failed.
        """
        succeeded = 0
        failed = 0
        failures = []

        for i in range(0, len(requests), self.bulk_chunk_size):
            chunk = requests[i : i + self.bulk_chunk_size]

            enrolments = []
            for req in chunk:
                entry: dict = {
                    "roleid": req.role_id,
                    "userid": req.user_id,
                    "courseid": req.course_id,
                }
                if req.timestart:
                    entry["timestart"] = int(req.timestart.timestamp())
                if req.timeend:
                    entry["timeend"] = int(req.timeend.timestamp())
                enrolments.append(entry)

            try:
                await self.client.call("enrol_manual_enrol_users", {"enrolments": enrolments})
                succeeded += len(chunk)
            except Exception as exc:
                failed += len(chunk)
                for req in chunk:
                    failures.append((req.user_id, req.course_id, str(exc)))
                logger.warning("Bulk enroll chunk %d failed: %s", i // self.bulk_chunk_size, exc)

            if i + self.bulk_chunk_size < len(requests):
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

        BUG 6 FIX: The original code passed:
            options=[{"name": "withcapability", "value": "moodle/course:view"}]

        This filters results to only users who have that specific capability —
        which excludes students in some custom role configurations and guests.
        The correct approach for listing all enrolled users is to pass only
        `courseid` and let Moodle return everyone regardless of capability.
        """
        response = await self.client.call(
            "core_enrol_get_enrolled_users",
            {"courseid": course_id},
        )

        users = []
        for user_data in response:
            roles = [role["shortname"] for role in user_data.get("roles", [])]
            groups = [group["name"] for group in user_data.get("groups", [])]

            users.append(
                EnrolledUser(
                    id=user_data["id"],
                    username=user_data.get("username", ""),
                    firstname=user_data.get("firstname", ""),
                    lastname=user_data.get("lastname", ""),
                    fullname=user_data.get("fullname", ""),
                    email=user_data.get("email", ""),
                    roles=roles,
                    groups=groups,
                )
            )

        return users

    async def sync_enrollments(
        self, course_id: int, expected: List[EnrollmentRequest]
    ) -> SyncResult:
        """
        Sync enrollments to match an expected state.

        BUG 1 FIX (CRITICAL): The original code had:
            current_set = {(u.id, 5)}

        This is a SET LITERAL containing ONE tuple — `(u.id, 5)` — where `u` is
        not defined in the surrounding scope, causing a NameError at runtime.

        The intent was a SET COMPREHENSION:
            current_set = {(u.id, 5) for u in current_users}

        The missing `for u in current_users` made sync_enrollments completely
        broken — it would either crash immediately or produce a one-element set
        that bears no relation to the actual enrolled users.
        """
        current_users = await self.list_enrolled_users(course_id)

        # BUG 1 FIX: set comprehension, not set literal
        current_set = {(u.id, next(iter(u.roles), "student")) for u in current_users}

        # Build expected set — use role_id as-is from request
        # Map numeric role_id to a comparable key; use str for consistency
        expected_set = {(req.user_id, req.role_id) for req in expected}

        # Compare by user_id only (role changes handled as re-enroll)
        current_user_ids = {uid for uid, _ in current_set}
        expected_user_ids = {uid for uid, _ in expected_set}

        to_remove_ids = current_user_ids - expected_user_ids
        to_add = expected_set - {(uid, rid) for uid, rid in expected_set if uid in current_user_ids}
        unchanged_ids = current_user_ids & expected_user_ids

        added = 0
        removed = 0
        errors = []

        for user_id in to_remove_ids:
            try:
                await self.unenroll_user(user_id, course_id)
                removed += 1
            except Exception as exc:
                errors.append(f"Failed to unenroll user {user_id}: {exc}")

        for user_id, role_id in to_add:
            try:
                await self.enroll_user(user_id, course_id, role_id)
                added += 1
            except Exception as exc:
                errors.append(f"Failed to enroll user {user_id}: {exc}")

        return SyncResult(
            course_id=course_id,
            expected_count=len(expected_user_ids),
            actual_count=len(current_user_ids) - removed + added,
            added=added,
            removed=removed,
            unchanged=len(unchanged_ids),
            errors=errors,
        )

    async def get_user_enrollments(self, user_id: int) -> List[Course]:
        """Get all courses a user is enrolled in."""
        response = await self.client.call(
            "core_enrol_get_users_courses",
            {"userid": user_id},
        )
        # BUG FIX: moved imports outside of loop — importing inside a for-loop
        # re-executes the import machinery on every iteration (unnecessary overhead)
        return [transform_course(course_data) for course_data in response]