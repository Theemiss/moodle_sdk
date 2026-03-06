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
    Section,
    Module,
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

        Args:
            category_id: Optional category ID to filter by

        Returns:
            List of courses
        """
        params = {}
        if category_id:
            params["criteria"] = [{"key": "category", "value": category_id}]

        response = await self.client.call("core_course_get_courses", params)
        if not isinstance(response, list):
            response = [response]

        return [transform_course(course) for course in response]

    async def get_course(self, course_id: int) -> Course:
        """
        Get a single course by ID.

        Args:
            course_id: Course ID

        Returns:
            Course object

        Raises:
            MoodleNotFoundError: If course doesn't exist
        """
        response = await self.client.call("core_course_get_courses", {"options": {"ids": [course_id]}})

        if not response or len(response) == 0:
            raise MoodleNotFoundError("core_course_get_courses", "Course", course_id)

        return transform_course(response[0])

    async def create_course(self, data: CourseCreate) -> Course:
        """
        Create a new course.

        Args:
            data: Course creation data

        Returns:
            Created course
        """
        # Convert datetime to timestamp if present
        course_data = data.model_dump(exclude_none=True)
        if data.startdate:
            course_data["startdate"] = int(data.startdate.timestamp())
        if data.enddate:
            course_data["enddate"] = int(data.enddate.timestamp())

        response = await self.client.call(
            "core_course_create_courses",
            {"courses": [course_data]},
        )

        if not response or len(response) == 0:
            raise RuntimeError("Course creation returned empty response")

        return await self.get_course(response[0]["id"])

    async def update_course(self, course_id: int, data: CourseUpdate) -> Course:
        """
        Update an existing course.

        Args:
            course_id: Course ID
            data: Update data (only provided fields will be updated)

        Returns:
            Updated course
        """
        # Convert to dict and remove None values
        update_data = data.model_dump(exclude_none=True)

        # Convert datetime to timestamp
        if "startdate" in update_data and update_data["startdate"]:
            update_data["startdate"] = int(update_data["startdate"].timestamp())
        if "enddate" in update_data and update_data["enddate"]:
            update_data["enddate"] = int(update_data["enddate"].timestamp())

        # Add ID to the update
        update_data["id"] = course_id

        await self.client.call("core_course_update_courses", {"courses": [update_data]})
        return await self.get_course(course_id)

    async def duplicate_course(
        self,
        source_id: int,
        new_shortname: str,
        new_fullname: str,
        category_id: Optional[int] = None,
    ) -> Course:
        """
        Duplicate an existing course.

        Args:
            source_id: Source course ID
            new_shortname: New course short name
            new_fullname: New course full name
            category_id: New category ID (defaults to source category)

        Returns:
            Newly created course
        """
        params = {
            "courseid": source_id,
            "fullname": new_fullname,
            "shortname": new_shortname,
        }

        if category_id:
            params["categoryid"] = category_id

        response = await self.client.call("core_course_duplicate_course", params)

        if "id" not in response:
            raise RuntimeError(f"Duplicate operation failed: {response.get('message', 'Unknown error')}")

        return await self.get_course(response["id"])

    async def archive_course(self, course_id: int, archive_category_id: Optional[int] = None) -> bool:
        """
        Archive a course (soft delete - hide and move to archive category).

        Args:
            course_id: Course ID
            archive_category_id: Category to move to (if None, keeps current category)

        Returns:
            True if successful
        """
        course = await self.get_course(course_id)

        # Hide the course
        update_data = CourseUpdate(visible=0)

        # Move to archive category if specified
        if archive_category_id:
            update_data.categoryid = archive_category_id

        await self.update_course(course_id, update_data)
        return True

    async def get_course_structure(self, course_id: int) -> CourseStructure:
        """
        Get the structure (sections and modules) of a course.

        Args:
            course_id: Course ID

        Returns:
            Course structure with sections and modules
        """
        response = await self.client.call("core_course_get_contents", {"courseid": course_id})
        sections = transform_sections(response)
        return CourseStructure(course_id=course_id, sections=sections)

    async def bulk_create_courses(self, courses: List[CourseCreate]) -> List[Course]:
        """
        Bulk create multiple courses.

        Args:
            courses: List of course creation data

        Returns:
            List of created courses
        """
        results = []
        failed = []

        # Process in chunks
        for i in range(0, len(courses), self.bulk_chunk_size):
            chunk = courses[i : i + self.bulk_chunk_size]
            chunk_results = []

            for course in chunk:
                try:
                    created = await self.create_course(course)
                    chunk_results.append(created)
                except Exception as e:
                    failed.append((course.shortname, str(e)))

            results.extend(chunk_results)

            # Small delay between chunks to avoid rate limiting
            if i + self.bulk_chunk_size < len(courses):
                await asyncio.sleep(0.5)

        if failed:
            raise BulkOperationError(
                "Bulk course creation partially failed",
                succeeded=[c.id for c in results],
                failed=[(-1, f"{name}: {err}") for name, err in failed],
            )

        return results