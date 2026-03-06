"""Activity log Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ActivityLog(BaseModel):
    """Activity log entry model."""
    
    id: int = Field(..., description="Log ID")
    user_id: int = Field(..., description="User ID")
    course_id: int = Field(0, description="Course ID")
    timecreated: Optional[datetime] = Field(None, description="When the event occurred")
    event_name: str = Field("", description="Event name")
    component: str = Field("", description="Component name")
    action: str = Field("", description="Action")
    target: str = Field("", description="Target")
    object_table: Optional[str] = Field(None, description="Object table")
    object_id: Optional[int] = Field(None, description="Object ID")
    ip: Optional[str] = Field(None, description="IP address")


class EngagementMetric(BaseModel):
    """User engagement metrics."""
    
    user_id: int
    course_id: int
    total_logs: int = 0
    last_access: Optional[datetime] = None
    days_active: int = 0
    activity_types: int = 0
    engagement_score: float = 0.0