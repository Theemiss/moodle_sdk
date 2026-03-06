"""Grade-related Pydantic models."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class GradeItem(BaseModel):
    """Grade item in a course."""

    id: int
    itemname: str
    itemtype: str
    itemmodule: Optional[str] = None
    iteminstance: Optional[int] = None
    grademax: float
    grademin: float
    gradepass: float
    hidden: bool
    locked: bool
    weight: Optional[float] = None
    grade: Optional[float] = None


class StudentGrade(BaseModel):
    """Grade for a single student on a grade item."""

    user_id: int
    grade_item_id: int
    rawgrade: Optional[float] = None
    grade: Optional[float] = None
    percentage: Optional[float] = None
    lettergrade: Optional[str] = None
    feedback: Optional[str] = None
    feedbackformat: Optional[int] = None
    overridden: bool = False
    hidden: bool = False


class GradeReport(BaseModel):
    """Complete grade report for a course/user."""

    course_id: int
    user_id: int
    user_fullname: str
    grade_items: List[GradeItem] = Field(default_factory=list)
    grades: List[StudentGrade] = Field(default_factory=list)
    total_grade: Optional[float] = None
    total_percentage: Optional[float] = None


class GradeDistribution(BaseModel):
    """Statistical distribution of grades."""

    course_id: int
    total_students: int
    mean: float
    median: float
    std_dev: float
    percentiles: Dict[str, float] = Field(default_factory=dict)
    pass_rate: float
    grade_buckets: Dict[str, int] = Field(default_factory=dict)


class StudentPerformance(BaseModel):
    """Individual student performance metrics."""

    user_id: int
    user_fullname: str
    grade: float
    percentage: float
    z_score: float
    percentile_rank: float
    performance_band: str  # A/B/C/D/F
    above_average: bool