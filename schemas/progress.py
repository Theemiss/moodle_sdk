"""Progress and completion Pydantic models."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class ActivityCompletion(BaseModel):
    """Completion status for a single activity."""

    course_id: int
    cmid: int  # Course module ID
    activity_name: str
    activity_type: str
    user_id: int
    state: int  # 0=incomplete, 1=complete, 2=completepass, 3=completefail
    timecompleted: Optional[datetime] = None
    completion_expected: Optional[datetime] = None
    override_by: Optional[int] = None
    tracked: bool = True


class CompletionStatus(BaseModel):
    """Overall course completion status for a user."""

    course_id: int
    user_id: int
    completed: bool
    completion_percentage: float
    timecompleted: Optional[datetime] = None
    activities_completed: int
    total_activities: int
    activities: List[ActivityCompletion] = Field(default_factory=list)


class UserProgress(BaseModel):
    """Comprehensive user progress across courses."""

    user_id: int
    enrolled_courses: List[int] = Field(default_factory=list)
    course_completions: Dict[int, CompletionStatus] = Field(default_factory=dict)
    overall_completion_percentage: float = 0.0
    completed_courses: int = 0
    in_progress_courses: int = 0
    last_activity: Optional[datetime] = None