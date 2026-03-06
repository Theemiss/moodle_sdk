"""Course reset service."""

import asyncio
import logging
from typing import List, Optional

from client.exceptions import MoodleNotFoundError, BulkOperationError
from client.moodle_client import AsyncMoodleClient
from config.settings import settings
from schemas.reset import ResetOptions, ResetResult

logger = logging.getLogger(__name__)


class ResetService:
    """Service for resetting courses."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client
        self.bulk_chunk_size = settings.bulk_chunk_size

    def _prepare_reset_options(self, options: ResetOptions) -> dict:
        """Convert ResetOptions to Moodle API parameters."""
        return {
            # General
            "reset_start_date": 1 if options.reset_start_date else 0,
            "delete_events": 1 if options.delete_events else 0,
            # Completions and grades
            "reset_completion": 1 if options.reset_completion else 0,
            "reset_grades": 1 if options.reset_grades else 0,
            "reset_gradebook_items": 1 if options.reset_gradebook_items else 0,
            # Activities
            "reset_assign_submissions": 1 if options.reset_submissions else 0,
            "reset_quiz_attempts": 1 if options.reset_quiz_attempts else 0,
            "reset_forum_all": 1 if options.reset_forum_posts else 0,
            "reset_data": 1 if options.reset_database_entries else 0,
            "reset_glossary_all": 1 if options.reset_glossary_entries else 0,
            "reset_workshop_submissions": 1 if options.reset_workshop_submissions else 0,
            "reset_workshop_assessments": 1 if options.reset_workshop_assessments else 0,
            "reset_survey_answers": 1 if options.reset_survey_answers else 0,
            # Groups and roles
            "reset_groups_remove": 1 if options.reset_groups else 0,
            "reset_groupings_remove": 1 if options.reset_groupings else 0,
            "reset_roles_local": 1 if options.reset_roles else 0,
            "unenrol_users": options.unenrol_users,
            # Additional
            "reset_notes": 1 if options.reset_notes else 0,
            "reset_comments": 1 if options.reset_comments else 0,
            "reset_tags": 1 if options.reset_tags else 0,
        }

    async def reset_course(self, course_id: int, options: ResetOptions) -> ResetResult:
        """
        Reset a course with specified options.

        Args:
            course_id: Course ID to reset
            options: Reset options

        Returns:
            Reset result with status and warnings

        Raises:
            MoodleNotFoundError: If course doesn't exist
        """
        # Verify course exists
        try:
            await self.client.call("core_course_get_courses", {"options": {"ids": [course_id]}})
        except Exception as e:
            raise MoodleNotFoundError("core_course_reset_course", "Course", course_id) from e

        params = {
            "id": course_id,
            "options": self._prepare_reset_options(options),
        }

        response = await self.client.call("core_course_reset_course", params)

        # Parse response
        status = "success"
        warnings = response.get("warnings", [])

        if warnings:
            status = "partial"

        items_reset = []
        items_failed = []

        for warning in warnings:
            items_failed.append(warning.get("item", "unknown"))

        return ResetResult(
            course_id=course_id,
            status=status,
            message=response.get("message", "Course reset completed"),
            warnings=[w.get("message", "") for w in warnings],
            items_reset=items_reset,
            items_failed=items_failed,
        )

    async def reset_course_grades(self, course_id: int) -> ResetResult:
        """Reset only grades in a course."""
        options = ResetOptions(
            reset_grades=True,
            reset_gradebook_items=True,
            reset_completion=False,
            reset_submissions=False,
            reset_quiz_attempts=False,
        )
        return await self.reset_course(course_id, options)

    async def reset_course_completions(self, course_id: int) -> ResetResult:
        """Reset only completions in a course."""
        options = ResetOptions(
            reset_grades=False,
            reset_gradebook_items=False,
            reset_completion=True,
            reset_submissions=False,
            reset_quiz_attempts=False,
        )
        return await self.reset_course(course_id, options)

    async def reset_course_quiz_attempts(self, course_id: int) -> ResetResult:
        """Reset only quiz attempts in a course."""
        options = ResetOptions(
            reset_grades=False,
            reset_gradebook_items=False,
            reset_completion=False,
            reset_submissions=False,
            reset_quiz_attempts=True,
        )
        return await self.reset_course(course_id, options)

    async def reset_course_forum_posts(self, course_id: int) -> ResetResult:
        """Reset only forum posts in a course."""
        options = ResetOptions(
            reset_grades=False,
            reset_gradebook_items=False,
            reset_completion=False,
            reset_submissions=False,
            reset_quiz_attempts=False,
            reset_forum_posts=True,
        )
        return await self.reset_course(course_id, options)

    async def bulk_reset_courses(self, course_ids: List[int], options: ResetOptions) -> List[ResetResult]:
        """
        Reset multiple courses with the same options.

        Args:
            course_ids: List of course IDs
            options: Reset options to apply to all courses

        Returns:
            List of reset results
        """
        results = []
        failed = []

        for course_id in course_ids:
            try:
                result = await self.reset_course(course_id, options)
                results.append(result)
            except Exception as e:
                failed.append((course_id, str(e)))

            # Small delay between resets
            await asyncio.sleep(0.5)

        if failed:
            raise BulkOperationError(
                "Bulk reset partially failed",
                succeeded=[r.course_id for r in results],
                failed=failed,
            )

        return results