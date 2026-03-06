"""Pydantic schemas for Moodle data models."""

from schemas.course import (
    Course,
    CourseBase,
    CourseCreate,
    CourseUpdate,
    CourseStructure,
    Module,
    Section,
)
from schemas.enrollment import (
    BulkEnrollRequest,
    BulkEnrollResult,
    Enrollment,
    EnrollmentRequest,
    EnrolledUser,
    SyncResult,
)
from schemas.grade import (
    GradeDistribution,
    GradeItem,
    GradeReport,
    StudentGrade,
    StudentPerformance,
)
from schemas.progress import (
    ActivityCompletion,
    CompletionStatus,
    UserProgress,
)
from schemas.reset import ResetOptions, ResetResult
from schemas.user import (
    MoodleUser,
    UserRole,
    UserSearchQuery,
)
from schemas.activity import ActivityLog, EngagementMetric  # Add this line

__all__ = [
    # Course
    "Course",
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseStructure",
    "Section",
    "Module",
    # Enrollment
    "Enrollment",
    "EnrollmentRequest",
    "BulkEnrollRequest",
    "BulkEnrollResult",
    "EnrolledUser",
    "SyncResult",
    # Grade
    "GradeReport",
    "GradeItem",
    "StudentGrade",
    "GradeDistribution",
    "StudentPerformance",
    # Progress
    "CompletionStatus",
    "ActivityCompletion",
    "UserProgress",
    # Reset
    "ResetOptions",
    "ResetResult",
    # User
    "MoodleUser",
    "UserRole",
    "UserSearchQuery",
    "ActivityLog",  # Add this
    "EngagementMetric",  # Add this
]