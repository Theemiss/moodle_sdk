"""Admin-related Pydantic models using only real data."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class HealthComponent(BaseModel):
    """Individual component health status."""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    latency: Optional[int] = Field(None, description="Response latency in ms")
    details: Optional[str] = Field(None, description="Additional details")


class SystemHealth(BaseModel):
    """Overall system health status."""
    overall_status: str = Field(..., description="Overall system health")
    last_check: datetime = Field(..., description="Last health check time")
    response_time: int = Field(..., description="Overall response time in ms")
    components: List[HealthComponent] = Field(default_factory=list, description="Component health statuses")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")


class SystemStatus(BaseModel):
    """System status from available APIs."""
    version: str = Field(..., description="Moodle version")
    release: str = Field(..., description="Moodle release")
    site_url: str = Field(..., description="Site URL")
    site_name: str = Field(..., description="Site name")
    uptime: str = Field("Unknown", description="System uptime (not available via API)")
    last_cron: Optional[datetime] = Field(None, description="Last cron execution time")
    
    # Statistics
    total_users: int = Field(0, description="Total number of users")
    active_users: int = Field(0, description="Active users (last 30 days)")
    total_courses: int = Field(0, description="Total number of courses")
    active_courses: int = Field(0, description="Active courses")
    total_categories: int = Field(0, description="Total categories")
    disk_usage: str = Field("Unknown", description="Disk usage (not available via API)")
    db_size: str = Field("Unknown", description="Database size (not available via API)")
    plugins: List[Dict[str, Any]] = Field(default_factory=list, description="Plugin statuses (limited)")


class ScheduledTask(BaseModel):
    """Scheduled task information from core_cron_get_scheduled_tasks."""
    id: int = Field(..., description="Task ID")
    name: str = Field(..., description="Task name")
    type: str = Field(..., description="Task type")
    schedule: Optional[str] = Field(None, description="Cron schedule")
    last_run: Optional[datetime] = Field(None, description="Last run time")
    next_run: Optional[datetime] = Field(None, description="Next run time")
    status: str = Field(..., description="Task status (pending/running/completed/failed/disabled)")
    disabled: bool = Field(False, description="Whether task is disabled")


class TaskResult(BaseModel):
    """Task execution result."""
    success: bool = Field(..., description="Whether task succeeded")
    duration: Optional[int] = Field(None, description="Execution duration in ms")
    output: Optional[str] = Field(None, description="Task output")
    error: Optional[str] = Field(None, description="Error message if failed")