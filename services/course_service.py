"""Course management service."""

import asyncio
import logging
from typing import List, Optional

from client.exceptions import MoodleNotFoundError, BulkOperationError
from client.moodle_client import AsyncMoodleClient
from config.settings import settings
from schemas.course import (
    Course,
    CourseCreate,
    CourseStructure,
    CourseUpdate,
)
from utils.transformers import transform_course, transform_sections

logger = logging.getLogger(__name__)


class CourseService:
    """Service for course management operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client
        self.bulk_chunk_size = settings.bulk_chunk_size

    async def list_courses(self, category_id: Optional[int] = None) -> List[Course]:
        """
        List all courses, optionally filtered by category.

        When category_id is provided, uses core_course_get_courses_by_field with
        field=category — this is the correct Moodle 5 server-side filter, avoiding
        a full fetch + client-side scan.

        When no filter is provided, uses core_course_get_courses with no params
        which returns all visible courses the token has access to.
        """
        if category_id is not None:
            # Server-side category filter — single round trip, no client scanning
            response = await self.client.call(
                "core_course_get_courses_by_field",
                {"field": "category", "value": category_id},
            )
            # Response shape: {"courses": [...], "warnings": [...]}
            raw_list = response.get("courses", []) if isinstance(response, dict) else response
        else:
            raw_list = await self.client.call("core_course_get_courses", {})

        if not isinstance(raw_list, list):
            raw_list = [raw_list]

        return [transform_course(c) for c in raw_list]

    async def get_course(self, course_id: int) -> Course:
        """
        Get a single course by ID.

        Uses core_course_get_courses_by_field which is the correct Moodle 5 API
        for single-course lookup by ID. It accepts a field/value pair and returns
        a list with just that course.

        Why not core_course_get_courses with courseids[]?
        Moodle 5 rejects the courseids[] parameter with invalidparameter on many
        configurations — that endpoint is designed for bulk fetching all courses,
        not filtered lookups.

        Fallback: if get_by_field fails for any reason, scan the full course list
        (same call as list_courses — proven to work).
        """
        # Primary: core_course_get_courses_by_field — built for this exact use case
        try:
            response = await self.client.call(
                "core_course_get_courses_by_field",
                {"field": "id", "value": course_id},
            )
            # Response shape: {"courses": [...], "warnings": [...]}
            courses = response.get("courses", []) if isinstance(response, dict) else response
            if isinstance(courses, list) and courses:
                return transform_course(courses[0])
        except Exception as exc:
            logger.debug("get_course by_field failed for %d: %s", course_id, exc)

        # Fallback: full list scan (slower but always works)
        logger.debug("get_course falling back to full list scan for course %d", course_id)
        try:
            all_courses = await self.client.call("core_course_get_courses", {})
            if isinstance(all_courses, list):
                for raw in all_courses:
                    if raw.get("id") == course_id:
                        return transform_course(raw)
        except Exception as exc:
            logger.debug("get_course fallback list scan failed: %s", exc)

        raise MoodleNotFoundError("core_course_get_courses_by_field", "Course", course_id)

    async def create_course(self, data: CourseCreate) -> Course:
        """
        Create a new course.

        BUG 5 FIX: The original code called model_dump() to get course_data (which
        contains datetime objects for startdate/enddate), then overwrote those fields
        using `data.startdate` — which is correct but fragile. Additionally, any other
        datetime fields added in the future would silently break.

        Fix: use model_dump(mode='json') to force all fields to JSON-safe types first,
        then convert the ISO string timestamps to Unix integers that Moodle expects.
        """
        # mode='json' converts datetimes to ISO strings, enums to values, etc.
        course_dict = data.model_dump(exclude_none=True, mode="json")

        # Moodle expects Unix timestamps (int), not ISO strings
        for date_field in ("startdate", "enddate"):
            if date_field in course_dict and course_dict[date_field]:
                # model_dump(mode='json') gives us an ISO string — convert to timestamp
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(course_dict[date_field])
                course_dict[date_field] = int(dt.timestamp())

        response = await self.client.call(
            "core_course_create_courses",
            {"courses": [course_dict]},
        )

        if not response or len(response) == 0:
            raise RuntimeError("Course creation returned empty response from Moodle")

        return await self.get_course(response[0]["id"])

    async def update_course(self, course_id: int, data: CourseUpdate) -> Course:
        """Update an existing course."""
        update_dict = data.model_dump(exclude_none=True, mode="json")

        for date_field in ("startdate", "enddate"):
            if date_field in update_dict and update_dict[date_field]:
                from datetime import datetime
                dt = datetime.fromisoformat(update_dict[date_field])
                update_dict[date_field] = int(dt.timestamp())

        update_dict["id"] = course_id

        await self.client.call(
            "core_course_update_courses",
            {"courses": [update_dict]},
        )
        return await self.get_course(course_id)

    async def duplicate_course(
        self,
        source_id: int,
        new_shortname: str,
        new_fullname: str,
        category_id: Optional[int] = None,
    ) -> Course:
        """Duplicate an existing course."""
        params: dict = {
            "courseid": source_id,
            "fullname": new_fullname,
            "shortname": new_shortname,
        }
        if category_id is not None:
            params["categoryid"] = category_id

        response = await self.client.call("core_course_duplicate_course", params)

        if not isinstance(response, dict) or "id" not in response:
            raise RuntimeError(
                f"Duplicate operation returned unexpected response: {response}"
            )

        return await self.get_course(response["id"])

    async def archive_course(
        self, course_id: int, archive_category_id: Optional[int] = None
    ) -> bool:
        """
        Archive a course (soft delete: hide + move to archive category).

        BUG 6 FIX: The original code did:
            update_data = CourseUpdate(visible=0)
            update_data.categoryid = archive_category_id  ← WRONG

        Pydantic v2 models are not plain Python objects — you cannot set arbitrary
        attributes after construction unless the model is configured with extra="allow".
        Setting `.categoryid` on a frozen or standard Pydantic model silently does
        nothing (or raises ValidationError). The fix is to pass all fields at construction.
        """
        update_fields: dict = {"visible": 0}
        if archive_category_id is not None:
            update_fields["categoryid"] = archive_category_id

        update_data = CourseUpdate(**update_fields)
        await self.update_course(course_id, update_data)
        return True

    async def get_course_structure(self, course_id: int) -> CourseStructure:
        """Get course sections and modules."""
        response = await self.client.call(
            "core_course_get_contents",
            {"courseid": course_id},
        )
        sections = transform_sections(response)
        return CourseStructure(course_id=course_id, sections=sections)

    async def bulk_create_courses(self, courses: List[CourseCreate]) -> List[Course]:
        """Bulk create multiple courses in chunks."""
        results: List[Course] = []
        failed: list = []

        for i in range(0, len(courses), self.bulk_chunk_size):
            chunk = courses[i : i + self.bulk_chunk_size]

            for course in chunk:
                try:
                    created = await self.create_course(course)
                    results.append(created)
                except Exception as exc:
                    failed.append((course.shortname, str(exc)))
                    logger.warning("Failed to create course %s: %s", course.shortname, exc)

            if i + self.bulk_chunk_size < len(courses):
                await asyncio.sleep(0.5)

        if failed:
            raise BulkOperationError(
                "Bulk course creation partially failed",
                succeeded=[c.id for c in results],
                failed=[(-1, f"{name}: {err}") for name, err in failed],
            )

        return results