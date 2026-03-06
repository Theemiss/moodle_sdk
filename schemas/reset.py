"""Course reset options and results."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ResetOptions(BaseModel):
    """Options for resetting a course."""

    # General
    reset_start_date: bool = Field(False, description="Reset course start date")
    delete_events: bool = Field(False, description="Delete calendar events")

    # Completions and grades
    reset_completion: bool = Field(True, description="Reset activity completion")
    reset_grades: bool = Field(True, description="Reset grades")
    reset_gradebook_items: bool = Field(True, description="Reset gradebook items")

    # Activities
    reset_submissions: bool = Field(True, description="Delete assignment submissions")
    reset_quiz_attempts: bool = Field(True, description="Delete quiz attempts")
    reset_forum_posts: bool = Field(True, description="Delete forum posts")
    reset_database_entries: bool = Field(False, description="Delete database entries")
    reset_glossary_entries: bool = Field(False, description="Delete glossary entries")
    reset_workshop_submissions: bool = Field(False, description="Delete workshop submissions")
    reset_workshop_assessments: bool = Field(False, description="Delete workshop assessments")
    reset_survey_answers: bool = Field(False, description="Delete survey answers")

    # Groups and roles
    reset_groups: bool = Field(False, description="Delete groups")
    reset_groupings: bool = Field(False, description="Delete groupings")
    reset_roles: bool = Field(False, description="Delete role assignments")
    unenrol_users: List[str] = Field(
        default_factory=list,
        description="Role shortnames to unenroll",
    )

    # Additional options
    reset_notes: bool = Field(False, description="Delete notes")
    reset_comments: bool = Field(False, description="Delete comments")
    reset_tags: bool = Field(False, description="Delete tags")


class ResetResult(BaseModel):
    """Result of course reset operation."""

    course_id: int
    status: str  # "success", "partial", "failed"
    message: str
    warnings: List[str] = Field(default_factory=list)
    items_reset: List[str] = Field(default_factory=list)
    items_failed: List[str] = Field(default_factory=list)