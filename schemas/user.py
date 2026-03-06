"""User-related Pydantic models."""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, EmailStr


class UserRole(BaseModel):
    """User role in a context."""

    roleid: int
    name: str
    shortname: str
    contextid: int
    contextlevel: str
    courseid: Optional[int] = None


class MoodleUser(BaseModel):
    """Moodle user model."""

    id: int
    username: str
    firstname: str
    lastname: str
    fullname: str
    email: EmailStr
    idnumber: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    phone1: Optional[str] = None
    phone2: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    lang: str = "en"
    timezone: str = "99"
    firstaccess: Optional[datetime] = None
    lastaccess: Optional[datetime] = None
    lastlogin: Optional[datetime] = None
    currentlogin: Optional[datetime] = None
    auth: str = "manual"
    confirmed: bool = True
    suspended: bool = False
    deleted: bool = False
    profileimageurl: Optional[str] = None
    profileimageurlsmall: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=list)
    enrolled_courses: Optional[List[int]] = None


class UserSearchQuery(BaseModel):
    """Search parameters for finding users."""

    query: Optional[str] = Field(None, description="Search string")
    idnumber: Optional[str] = Field(None, description="ID number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    username: Optional[str] = Field(None, description="Username")
    firstname: Optional[str] = Field(None, description="First name")
    lastname: Optional[str] = Field(None, description="Last name")
    courseid: Optional[int] = Field(None, description="Limit to course")
    limit: int = Field(100, description="Max results", ge=1, le=1000)
    page: int = Field(0, description="Page number", ge=0)