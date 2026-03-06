"""Content and activity management service."""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from client.exceptions import MoodleNotFoundError
from client.moodle_client import AsyncMoodleClient
from schemas.content import (
    Activity,
    ActivityType,
    ActivityDetail,
    ModuleInfo,
    ActivityCompletionDetail,
    ActivityGrades,
    ActivityAttempt,
    ActivitySettings,
    CourseContent,
    SectionContent,
)
from utils.transformers import  transform_module_info

logger = logging.getLogger(__name__)


class ContentService:
    """Service for detailed course content and activity operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def get_course_activities(self, course_id: int) -> List[Activity]:
        """
        Get all activities in a course with basic information.
        
        Args:
            course_id: Course ID
            
        Returns:
            List of activities with basic details
        """
        # Get course structure first
        response = await self.client.call(
            "core_course_get_contents",
            {"courseid": course_id}
        )
        
        activities = []
        for section in response:
            section_num = section.get("section", 0)
            section_name = section.get("name", f"Section {section_num}")
            
            for module in section.get("modules", []):
                activity = Activity(
                    id=module.get("id", 0),
                    course_id=course_id,
                    section_id=section.get("id", 0),
                    section_number=section_num,
                    section_name=section_name,
                    name=module.get("name", ""),
                    modname=module.get("modname", ""),
                    instance=module.get("instance", 0),
                    description=module.get("description", ""),
                    visible=module.get("visible", 1),
                    visibleoncoursepage=module.get("visibleoncoursepage", 1),
                    url=module.get("url", ""),
                    completion=module.get("completion", 0),
                    completionexpected=module.get("completionexpected"),
                    dates=[{
                        "label": d.get("label", ""),
                        "timestamp": d.get("timestamp", 0),
                        "dataid": d.get("dataid", 0)
                    } for d in module.get("dates", [])],
                    contents=[{
                        "type": c.get("type", ""),
                        "filename": c.get("filename", ""),
                        "fileurl": c.get("fileurl", ""),
                        "filesize": c.get("filesize", 0),
                        "timecreated": c.get("timecreated"),
                        "timemodified": c.get("timemodified")
                    } for c in module.get("contents", [])]
                )
                activities.append(activity)
        
        return activities

    async def get_activity_detail(self, cmid: int) -> ActivityDetail:
        """
        Get detailed information about a specific activity.
        
        Args:
            cmid: Course module ID
            
        Returns:
            Detailed activity information
        """
        # Get module information
        module_info = await self._get_module_info(cmid)
        
        # Get activity-specific details based on type
        activity_detail = ActivityDetail(
            id=cmid,
            course_id=module_info.course_id,
            name=module_info.name,
            modname=module_info.modname,
            instance=module_info.instance,
            description=module_info.description,
            visible=module_info.visible,
            section_id=module_info.section_id,
            section_number=module_info.section_number,
            section_name=module_info.section_name,
            completion=module_info.completion,
            completionexpected=module_info.completionexpected,
            contents=module_info.contents,
        )
        
        # Fetch type-specific details
        if module_info.modname == "assign":
            details = await self._get_assignment_details(module_info.instance)
            activity_detail.assignment_details = details
        elif module_info.modname == "quiz":
            details = await self._get_quiz_details(module_info.instance)
            activity_detail.quiz_details = details
        elif module_info.modname == "forum":
            details = await self._get_forum_details(module_info.instance)
            activity_detail.forum_details = details
        elif module_info.modname == "scorm":
            details = await self._get_scorm_details(module_info.instance)
            activity_detail.scorm_details = details
        elif module_info.modname == "h5pactivity":
            details = await self._get_h5p_details(module_info.instance)
            activity_detail.h5p_details = details
        elif module_info.modname == "resource":
            details = await self._get_resource_details(module_info.instance)
            activity_detail.resource_details = details
        elif module_info.modname == "folder":
            details = await self._get_folder_details(module_info.instance)
            activity_detail.folder_details = details
        elif module_info.modname == "page":
            details = await self._get_page_details(module_info.instance)
            activity_detail.page_details = details
        elif module_info.modname == "url":
            details = await self._get_url_details(module_info.instance)
            activity_detail.url_details = details
        elif module_info.modname == "lesson":
            details = await self._get_lesson_details(module_info.instance)
            activity_detail.lesson_details = details
        elif module_info.modname == "glossary":
            details = await self._get_glossary_details(module_info.instance)
            activity_detail.glossary_details = details
        elif module_info.modname == "data":
            details = await self._get_database_details(module_info.instance)
            activity_detail.database_details = details
        elif module_info.modname == "workshop":
            details = await self._get_workshop_details(module_info.instance)
            activity_detail.workshop_details = details
        elif module_info.modname == "chat":
            details = await self._get_chat_details(module_info.instance)
            activity_detail.chat_details = details
        elif module_info.modname == "choice":
            details = await self._get_choice_details(module_info.instance)
            activity_detail.choice_details = details
        elif module_info.modname == "feedback":
            details = await self._get_feedback_details(module_info.instance)
            activity_detail.feedback_details = details
        
        return activity_detail

    async def get_user_activity_completion(
        self, course_id: int, user_id: int, cmid: Optional[int] = None
    ) -> List[ActivityCompletionDetail]:
        """
        Get completion status for activities for a specific user.
        
        Args:
            course_id: Course ID
            user_id: User ID
            cmid: Optional specific activity CMID
            
        Returns:
            List of activity completion details
        """
        params = {
            "courseid": course_id,
            "userid": user_id
        }
        
        response = await self.client.call(
            "core_completion_get_activities_completion_status",
            params
        )
        
        completions = []
        for status in response.get("statuses", []):
            if cmid and status.get("cmid") != cmid:
                continue
                
            completion = ActivityCompletionDetail(
                cmid=status.get("cmid", 0),
                course_id=course_id,
                user_id=user_id,
                state=status.get("state", 0),
                timecompleted=status.get("timecompleted"),
                completion_expected=status.get("completionexpected"),
                override_by=status.get("overrideby"),
                tracked=status.get("tracked", True),
                value=status.get("value"),
                grade=status.get("grade"),
                passgrade=status.get("passgrade"),
                has_completion=status.get("hascompletion", False),
                is_automatic=status.get("isautomatic", False),
                is_manual=status.get("ismanual", False)
            )
            completions.append(completion)
        
        return completions

    async def get_activity_grades(
        self, course_id: int, activity_id: int, activity_type: str
    ) -> ActivityGrades:
        """
        Get grades for a specific activity.
        
        Args:
            course_id: Course ID
            activity_id: Activity instance ID
            activity_type: Type of activity (assign, quiz, etc.)
            
        Returns:
            Activity grade information
        """
        # Map activity type to appropriate grade function
        grade_functions = {
            "assign": "mod_assign_get_grades",
            "quiz": "mod_quiz_get_user_attempts",
            "lesson": "mod_lesson_get_user_grade",
            "workshop": "mod_workshop_get_grades",
            "scorm": "mod_scorm_get_user_attempts",
        }
        
        function = grade_functions.get(activity_type)
        if not function:
            # Generic grade retrieval
            params = {
                "courseid": course_id,
                "itemname": f"{activity_type}_{activity_id}"
            }
            response = await self.client.call(
                "gradereport_user_get_grade_items",
                params
            )
            return ActivityGrades(
                activity_id=activity_id,
                activity_type=activity_type,
                grades=response.get("grades", [])
            )
        
        # Type-specific grade retrieval
        params = {f"{activity_type}id": activity_id}
        response = await self.client.call(function, params)
        
        return ActivityGrades(
            activity_id=activity_id,
            activity_type=activity_type,
            grades=response.get("grades", []),
            maxgrade=response.get("maxgrade"),
            gradepass=response.get("gradepass"),
        )

    async def get_activity_attempts(
        self, activity_id: int, activity_type: str, user_id: Optional[int] = None
    ) -> List[ActivityAttempt]:
        """
        Get user attempts for an activity (quizzes, SCORM, etc.).
        
        Args:
            activity_id: Activity instance ID
            activity_type: Type of activity
            user_id: Optional user ID to filter
            
        Returns:
            List of activity attempts
        """
        attempt_functions = {
            "quiz": "mod_quiz_get_user_attempts",
            "scorm": "mod_scorm_get_user_attempts",
            "lesson": "mod_lesson_get_user_attempts",
            "assign": "mod_assign_get_submission_status",
        }
        
        function = attempt_functions.get(activity_type)
        if not function:
            return []
        
        params = {f"{activity_type}id": activity_id}
        if user_id:
            params["userid"] = user_id
        
        response = await self.client.call(function, params)
        
        attempts = []
        for attempt_data in response.get("attempts", []):
            attempt = ActivityAttempt(
                id=attempt_data.get("id", 0),
                activity_id=activity_id,
                activity_type=activity_type,
                user_id=attempt_data.get("userid", user_id),
                attempt_number=attempt_data.get("attempt", 1),
                time_start=attempt_data.get("timestart"),
                time_finish=attempt_data.get("timefinish"),
                status=attempt_data.get("state", "inprogress"),
                score=attempt_data.get("sumgrades"),
                maxscore=attempt_data.get("maxgrade"),
                percentage=attempt_data.get("percentage"),
                feedback=attempt_data.get("feedback"),
            )
            attempts.append(attempt)
        
        return attempts

    async def update_activity_settings(
        self, cmid: int, settings: ActivitySettings
    ) -> bool:
        """
        Update activity settings.
        
        Args:
            cmid: Course module ID
            settings: New settings to apply
            
        Returns:
            True if successful
        """
        # Get module info first
        module_info = await self._get_module_info(cmid)
        
        # Map to appropriate update function
        update_functions = {
            "assign": "mod_assign_update_activity_settings",
            "quiz": "mod_quiz_update_settings",
            "forum": "mod_forum_update_settings",
            "resource": "mod_resource_update_settings",
            "folder": "mod_folder_update_settings",
            "page": "mod_page_update_settings",
            "url": "mod_url_update_settings",
            "lesson": "mod_lesson_update_settings",
        }
        
        function = update_functions.get(module_info.modname)
        if not function:
            raise ValueError(f"Update not supported for {module_info.modname}")
        
        params = {
            "cmid": cmid,
            "settings": settings.model_dump(exclude_none=True)
        }
        
        await self.client.call(function, params)
        return True

    async def toggle_activity_visibility(self, cmid: int, visible: bool) -> bool:
        """
        Show or hide an activity.
        
        Args:
            cmid: Course module ID
            visible: True to show, False to hide
            
        Returns:
            True if successful
        """
        params = {
            "cmid": cmid,
            "visible": 1 if visible else 0
        }
        
        await self.client.call("core_course_set_module_visibility", params)
        return True

    async def duplicate_activity(
        self, cmid: int, target_section: Optional[int] = None
    ) -> int:
        """
        Duplicate an activity.
        
        Args:
            cmid: Course module ID to duplicate
            target_section: Optional section ID to place duplicate in
            
        Returns:
            New CMID of duplicated activity
        """
        params = {
            "cmid": cmid,
        }
        if target_section:
            params["sectionid"] = target_section
        
        response = await self.client.call("core_course_duplicate_module", params)
        return response.get("cmid", 0)

    async def delete_activity(self, cmid: int) -> bool:
        """
        Delete an activity from the course.
        
        Args:
            cmid: Course module ID to delete
            
        Returns:
            True if successful
        """
        params = {"cmid": cmid}
        await self.client.call("core_course_delete_module", params)
        return True

    async def move_activity(
        self, cmid: int, target_section: int, before_cmid: Optional[int] = None
    ) -> bool:
        """
        Move an activity to a different section.
        
        Args:
            cmid: Course module ID to move
            target_section: Target section ID
            before_cmid: Optional CMID to place before
            
        Returns:
            True if successful
        """
        params = {
            "cmid": cmid,
            "sectionid": target_section,
        }
        if before_cmid:
            params["beforecmid"] = before_cmid
        
        await self.client.call("core_course_move_module", params)
        return True

    async def get_section_activities(self, course_id: int, section_id: int) -> List[Activity]:
        """
        Get all activities in a specific section.
        
        Args:
            course_id: Course ID
            section_id: Section ID
            
        Returns:
            List of activities in the section
        """
        all_activities = await self.get_course_activities(course_id)
        return [a for a in all_activities if a.section_id == section_id]

    async def get_activities_by_type(
        self, course_id: int, activity_type: str
    ) -> List[Activity]:
        """
        Get all activities of a specific type in a course.
        
        Args:
            course_id: Course ID
            activity_type: Type of activity (assign, quiz, forum, etc.)
            
        Returns:
            List of activities of the specified type
        """
        all_activities = await self.get_course_activities(course_id)
        return [a for a in all_activities if a.modname == activity_type]

    async def get_course_content_summary(self, course_id: int) -> CourseContent:
        """
        Get a summary of all content in a course.
        
        Args:
            course_id: Course ID
            
        Returns:
            Course content summary with statistics
        """
        activities = await self.get_course_activities(course_id)
        
        # Group by section
        sections = {}
        activity_types = {}
        
        for activity in activities:
            # Group by section
            if activity.section_id not in sections:
                sections[activity.section_id] = SectionContent(
                    id=activity.section_id,
                    number=activity.section_number,
                    name=activity.section_name,
                    activities=[]
                )
            sections[activity.section_id].activities.append(activity)
            
            # Count by type
            activity_types[activity.modname] = activity_types.get(activity.modname, 0) + 1
        
        return CourseContent(
            course_id=course_id,
            total_activities=len(activities),
            total_sections=len(sections),
            sections=list(sections.values()),
            activity_types=activity_types,
            completion_tracking_enabled=any(a.completion for a in activities)
        )

    # Private helper methods for type-specific details
    async def _get_module_info(self, cmid: int) -> ModuleInfo:
        """Get basic module information."""
        response = await self.client.call(
            "core_course_get_module",
            {"cmid": cmid}
        )
        return transform_module_info(response)

    async def _get_assignment_details(self, instance_id: int) -> Dict[str, Any]:
        """Get assignment-specific details."""
        response = await self.client.call(
            "mod_assign_get_assignments",
            {"assignmentids": [instance_id]}
        )
        assignments = response.get("courses", [])
        if assignments and assignments[0].get("assignments"):
            return assignments[0]["assignments"][0]
        return {}

    async def _get_quiz_details(self, instance_id: int) -> Dict[str, Any]:
        """Get quiz-specific details."""
        response = await self.client.call(
            "mod_quiz_get_quiz_access_information",
            {"quizid": instance_id}
        )
        return response

    async def _get_forum_details(self, instance_id: int) -> Dict[str, Any]:
        """Get forum-specific details."""
        response = await self.client.call(
            "mod_forum_get_forum_access_information",
            {"forumid": instance_id}
        )
        return response

    async def _get_scorm_details(self, instance_id: int) -> Dict[str, Any]:
        """Get SCORM-specific details."""
        response = await self.client.call(
            "mod_scorm_get_scorm_access_information",
            {"scormid": instance_id}
        )
        return response

    async def _get_h5p_details(self, instance_id: int) -> Dict[str, Any]:
        """Get H5P-specific details."""
        response = await self.client.call(
            "mod_h5pactivity_get_h5pactivity_access_information",
            {"h5pactivityid": instance_id}
        )
        return response

    async def _get_resource_details(self, instance_id: int) -> Dict[str, Any]:
        """Get resource-specific details."""
        response = await self.client.call(
            "mod_resource_get_resources_by_courses",
            {"resourceids": [instance_id]}
        )
        resources = response.get("resources", [])
        return resources[0] if resources else {}

    async def _get_folder_details(self, instance_id: int) -> Dict[str, Any]:
        """Get folder-specific details."""
        response = await self.client.call(
            "mod_folder_get_folders_by_courses",
            {"folderids": [instance_id]}
        )
        folders = response.get("folders", [])
        return folders[0] if folders else {}

    async def _get_page_details(self, instance_id: int) -> Dict[str, Any]:
        """Get page-specific details."""
        response = await self.client.call(
            "mod_page_get_pages_by_courses",
            {"pageids": [instance_id]}
        )
        pages = response.get("pages", [])
        return pages[0] if pages else {}

    async def _get_url_details(self, instance_id: int) -> Dict[str, Any]:
        """Get URL-specific details."""
        response = await self.client.call(
            "mod_url_get_urls_by_courses",
            {"urlids": [instance_id]}
        )
        urls = response.get("urls", [])
        return urls[0] if urls else {}

    async def _get_lesson_details(self, instance_id: int) -> Dict[str, Any]:
        """Get lesson-specific details."""
        response = await self.client.call(
            "mod_lesson_get_lesson_access_information",
            {"lessonid": instance_id}
        )
        return response

    async def _get_glossary_details(self, instance_id: int) -> Dict[str, Any]:
        """Get glossary-specific details."""
        response = await self.client.call(
            "mod_glossary_get_glossaries_by_courses",
            {"glossaryids": [instance_id]}
        )
        glossaries = response.get("glossaries", [])
        return glossaries[0] if glossaries else {}

    async def _get_database_details(self, instance_id: int) -> Dict[str, Any]:
        """Get database-specific details."""
        response = await self.client.call(
            "mod_data_get_databases_by_courses",
            {"databaseids": [instance_id]}
        )
        databases = response.get("databases", [])
        return databases[0] if databases else {}

    async def _get_workshop_details(self, instance_id: int) -> Dict[str, Any]:
        """Get workshop-specific details."""
        response = await self.client.call(
            "mod_workshop_get_workshop_access_information",
            {"workshopid": instance_id}
        )
        return response

    async def _get_chat_details(self, instance_id: int) -> Dict[str, Any]:
        """Get chat-specific details."""
        response = await self.client.call(
            "mod_chat_get_chats_by_courses",
            {"chatids": [instance_id]}
        )
        chats = response.get("chats", [])
        return chats[0] if chats else {}

    async def _get_choice_details(self, instance_id: int) -> Dict[str, Any]:
        """Get choice-specific details."""
        response = await self.client.call(
            "mod_choice_get_choices_by_courses",
            {"choiceids": [instance_id]}
        )
        choices = response.get("choices", [])
        return choices[0] if choices else {}

    async def _get_feedback_details(self, instance_id: int) -> Dict[str, Any]:
        """Get feedback-specific details."""
        response = await self.client.call(
            "mod_feedback_get_feedbacks_by_courses",
            {"feedbackids": [instance_id]}
        )
        feedbacks = response.get("feedbacks", [])
        return feedbacks[0] if feedbacks else {}