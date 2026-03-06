"""Enrollment-related Pydantic models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Enrollment(BaseModel):
    """Base enrollment model."""

    user_id: int
    course_id: int
    role_id: int = Field(5, description="Default role ID (5 = student)")
    timestart: Optional[datetime] = None
    timeend: Optional[datetime] = None


class EnrollmentRequest(BaseModel):
    """Request to enroll a single user."""

    user_id: int
    course_id: int
    role_id: int = 5
    timestart: Optional[datetime] = None
    timeend: Optional[datetime] = None


class BulkEnrollRequest(BaseModel):
    """Request for bulk enrollment."""

    enrollments: List[EnrollmentRequest] = Field(..., max_items=1000)


class EnrolledUser(BaseModel):
    """Enrolled user with additional course-specific info."""

    id: int
    username: str
    firstname: str
    lastname: str
    fullname: str
    email: str
    roles: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    enrolled_courses: Optional[List[int]] = None


class BulkEnrollResult(BaseModel):
    """Result of bulk enrollment operation."""

    total: int
    succeeded: int
    failed: int
    failures: List[tuple[int, int, str]] = Field(
        default_factory=list,
        description="List of (user_id, course_id, error_message)",
    )


class SyncResult(BaseModel):
    """Result of enrollment sync operation."""

    course_id: int
    expected_count: int
    actual_count: int
    added: int
    removed: int
    unchanged: int
    errors: List[str] = Field(default_factory=list)