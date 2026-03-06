"""Progress and completion tracking service."""

import logging
from typing import List, Optional

from client.exceptions import MoodleNotFoundError
from client.moodle_client import AsyncMoodleClient
from schemas.progress import (
    ActivityCompletion,
    CompletionStatus,
    UserProgress,
)

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for tracking user progress and completion."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def get_activity_completions(self, user_id: int, course_id: int) -> List[ActivityCompletion]:
        """
        Get completion status for all activities in a course for a user.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            List of activity completion statuses
        """
        params = {
            "courseid": course_id,
            "userid": user_id,
        }

        response = await self.client.call("core_completion_get_activities_completion_status", params)

        activities = []
        for status in response.get("statuses", []):
            activities.append(
                ActivityCompletion(
                    course_id=course_id,
                    cmid=status["cmid"],
                    activity_name=status.get("activityname", ""),
                    activity_type=status.get("modname", ""),
                    user_id=user_id,
                    state=status["state"],
                    timecompleted=status.get("timecompleted"),
                    completion_expected=status.get("completionexpected"),
                    override_by=status.get("overrideby"),
                    tracked=status.get("tracked", True),
                )
            )

        return activities

    async def get_course_completion(self, user_id: int, course_id: int) -> CompletionStatus:
        """
        Get overall course completion status for a user.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            Course completion status
        """
        params = {
            "courseid": course_id,
            "userid": user_id,
        }

        try:
            response = await self.client.call("core_completion_get_course_completion_status", params)

            completion_status = response.get("completionstatus", {})

            # Get detailed activity completions
            activities = await self.get_activity_completions(user_id, course_id)

            completed_activities = sum(1 for a in activities if a.state in (1, 2))
            total_activities = len(activities)
            percentage = (completed_activities / total_activities * 100) if total_activities > 0 else 0

            return CompletionStatus(
                course_id=course_id,
                user_id=user_id,
                completed=completion_status.get("completed", False),
                completion_percentage=percentage,
                timecompleted=completion_status.get("timecompleted"),
                activities_completed=completed_activities,
                total_activities=total_activities,
                activities=activities,
            )

        except Exception as e:
            # Handle case where completion tracking is not enabled
            logger.debug(f"Completion tracking not available for course {course_id}: {e}")
            return CompletionStatus(
                course_id=course_id,
                user_id=user_id,
                completed=False,
                completion_percentage=0,
                activities_completed=0,
                total_activities=0,
                activities=[],
            )

    async def get_user_progress(self, user_id: int) -> UserProgress:
        """
        Get comprehensive progress for a user across all enrolled courses.

        Args:
            user_id: User ID

        Returns:
            User progress across courses
        """
        # Get user's enrolled courses
        from services.enrollment_service import EnrollmentService

        enrollment_service = EnrollmentService(self.client)
        courses = await enrollment_service.get_user_enrollments(user_id)

        course_completions = {}
        completed = 0
        in_progress = 0

        for course in courses:
            completion = await self.get_course_completion(user_id, course.id)
            course_completions[course.id] = completion

            if completion.completed:
                completed += 1
            elif completion.total_activities > 0:
                in_progress += 1

        # Calculate overall percentage
        total_percentage = 0
        if course_completions:
            total_percentage = sum(c.completion_percentage for c in course_completions.values()) / len(
                course_completions
            )

        return UserProgress(
            user_id=user_id,
            enrolled_courses=[c.id for c in courses],
            course_completions=course_completions,
            overall_completion_percentage=total_percentage,
            completed_courses=completed,
            in_progress_courses=in_progress,
        )

    async def bulk_get_completions(self, user_ids: List[int], course_id: int) -> List[CompletionStatus]:
        """
        Get completion status for multiple users in a course.

        Args:
            user_ids: List of user IDs
            course_id: Course ID

        Returns:
            List of completion statuses
        """
        completions = []

        for user_id in user_ids:
            try:
                completion = await self.get_course_completion(user_id, course_id)
                completions.append(completion)
            except Exception as e:
                logger.warning(f"Failed to get completion for user {user_id}: {e}")

        return completions