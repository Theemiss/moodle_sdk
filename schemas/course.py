"""Course-related Pydantic models."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator


class CourseBase(BaseModel):
    """Base course model with common fields."""

    shortname: str = Field(..., description="Course short name")
    fullname: str = Field(..., description="Course full name")
    categoryid: int = Field(..., description="Category ID")
    idnumber: Optional[str] = Field(None, description="Course ID number")
    summary: Optional[str] = Field(None, description="Course summary")
    summaryformat: Optional[int] = Field(1, description="Summary format (1=HTML, 0=Plain)")
    format: Optional[str] = Field("topics", description="Course format")
    showgrades: Optional[int] = Field(1, description="Show grades")
    newsitems: Optional[int] = Field(5, description="Number of news items")
    startdate: Optional[datetime] = Field(None, description="Course start date")
    enddate: Optional[datetime] = Field(None, description="Course end date")
    visible: Optional[int] = Field(1, description="Course visibility")
    groupmode: Optional[int] = Field(0, description="Group mode")
    groupmodeforce: Optional[int] = Field(0, description="Force group mode")
    defaultgroupingid: Optional[int] = Field(0, description="Default grouping ID")
    lang: Optional[str] = Field("en", description="Course language")
    calendartype: Optional[str] = Field("gregorian", description="Calendar type")
    theme: Optional[str] = Field(None, description="Course theme")


class CourseCreate(CourseBase):
    """Model for creating a new course."""

    pass


class CourseUpdate(BaseModel):
    """Model for updating a course (all fields optional)."""

    shortname: Optional[str] = Field(None, description="Course short name")
    fullname: Optional[str] = Field(None, description="Course full name")
    categoryid: Optional[int] = Field(None, description="Category ID")
    idnumber: Optional[str] = Field(None, description="Course ID number")
    summary: Optional[str] = Field(None, description="Course summary")
    summaryformat: Optional[int] = Field(None, description="Summary format")
    format: Optional[str] = Field(None, description="Course format")
    showgrades: Optional[int] = Field(None, description="Show grades")
    newsitems: Optional[int] = Field(None, description="Number of news items")
    startdate: Optional[datetime] = Field(None, description="Course start date")
    enddate: Optional[datetime] = Field(None, description="Course end date")
    visible: Optional[int] = Field(None, description="Course visibility")
    groupmode: Optional[int] = Field(None, description="Group mode")
    groupmodeforce: Optional[int] = Field(None, description="Force group mode")
    defaultgroupingid: Optional[int] = Field(None, description="Default grouping ID")
    lang: Optional[str] = Field(None, description="Course language")
    calendartype: Optional[str] = Field(None, description="Calendar type")
    theme: Optional[str] = Field(None, description="Course theme")

    @field_validator("*", mode="before")
    def ignore_none_values(cls, v):
        """Remove None values from update payload."""
        return v


class Course(CourseBase):
    """Full course model with all fields from Moodle."""

    id: int = Field(..., description="Course ID")
    displayname: Optional[str] = Field(None, description="Display name")
    timecreated: Optional[datetime] = Field(None, description="Creation time")
    timemodified: Optional[datetime] = Field(None, description="Modification time")
    enablecompletion: Optional[int] = Field(0, description="Enable completion tracking")
    completionnotify: Optional[int] = Field(0, description="Completion notify")
    cacherev: Optional[int] = Field(None, description="Cache revision")


class Module(BaseModel):
    """Course module model."""

    id: int
    name: str
    instance: int
    modname: str
    modplural: str
    idnumber: Optional[str] = None
    completion: Optional[int] = None
    visible: int
    visibleoncoursepage: Optional[int] = None
    uservisible: Optional[bool] = None
    availabilityinfo: Optional[str] = None
    indent: Optional[int] = None


class Section(BaseModel):
    """Course section model."""

    id: int
    name: Optional[str] = None
    summary: Optional[str] = None
    summaryformat: int = 1
    section: int
    visible: int
    availabilityinfo: Optional[str] = None
    modules: List[Module] = Field(default_factory=list)


class CourseStructure(BaseModel):
    """Complete course structure with sections and modules."""

    course_id: int
    sections: List[Section] = Field(default_factory=list)