"""Content and activity Pydantic models."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    """Activity type enumeration."""
    ASSIGN = "assign"
    QUIZ = "quiz"
    FORUM = "forum"
    SCORM = "scorm"
    H5P = "h5pactivity"
    RESOURCE = "resource"
    FOLDER = "folder"
    PAGE = "page"
    URL = "url"
    LESSON = "lesson"
    GLOSSARY = "glossary"
    DATABASE = "data"
    WORKSHOP = "workshop"
    CHAT = "chat"
    CHOICE = "choice"
    FEEDBACK = "feedback"


class ActivityContent(BaseModel):
    """Content file within an activity."""
    type: str = Field("", description="Content type (file, url, etc.)")
    filename: str = Field("", description="Filename")
    fileurl: str = Field("", description="File URL")
    filesize: int = Field(0, description="File size in bytes")
    timecreated: Optional[int] = Field(None, description="Creation timestamp")
    timemodified: Optional[int] = Field(None, description="Modification timestamp")
    mimetype: Optional[str] = Field(None, description="MIME type")
    content: Optional[str] = Field(None, description="Text content")


class ActivityDate(BaseModel):
    """Date information for an activity."""
    label: str = Field("", description="Date label")
    timestamp: int = Field(0, description="Unix timestamp")
    dataid: int = Field(0, description="Date data ID")


class Activity(BaseModel):
    """Basic activity information."""
    id: int = Field(..., description="Course module ID")
    course_id: int = Field(..., description="Course ID")
    section_id: int = Field(0, description="Section ID")
    section_number: int = Field(0, description="Section number")
    section_name: str = Field("", description="Section name")
    name: str = Field("", description="Activity name")
    modname: str = Field("", description="Module name (assign, quiz, etc.)")
    instance: int = Field(0, description="Activity instance ID")
    description: str = Field("", description="Activity description")
    visible: int = Field(1, description="Visibility (1=visible, 0=hidden)")
    visibleoncoursepage: int = Field(1, description="Visible on course page")
    url: str = Field("", description="Activity URL")
    completion: int = Field(0, description="Completion tracking")
    completionexpected: Optional[int] = Field(None, description="Expected completion time")
    dates: List[ActivityDate] = Field(default_factory=list, description="Activity dates")
    contents: List[ActivityContent] = Field(default_factory=list, description="Activity contents")
    customdata: Optional[str] = Field(None, description="Custom activity data")


class ModuleInfo(BaseModel):
    """Detailed module information."""
    id: int = Field(..., description="Course module ID")
    course_id: int = Field(..., description="Course ID")
    name: str = Field("", description="Module name")
    modname: str = Field("", description="Module type")
    instance: int = Field(0, description="Instance ID")
    description: str = Field("", description="Module description")
    visible: int = Field(1, description="Visibility")
    section_id: int = Field(0, description="Section ID")
    section_number: int = Field(0, description="Section number")
    section_name: str = Field("", description="Section name")
    completion: int = Field(0, description="Completion tracking")
    completionexpected: Optional[int] = Field(None, description="Expected completion")
    contents: List[ActivityContent] = Field(default_factory=list, description="Module contents")
    url: str = Field("", description="Module URL")


class ActivityCompletionDetail(BaseModel):
    """Detailed activity completion information."""
    cmid: int = Field(..., description="Course module ID")
    course_id: int = Field(..., description="Course ID")
    user_id: int = Field(..., description="User ID")
    state: int = Field(0, description="Completion state (0=incomplete, 1=complete, 2=complete_pass, 3=complete_fail)")
    timecompleted: Optional[int] = Field(None, description="Completion timestamp")
    completion_expected: Optional[int] = Field(None, description="Expected completion time")
    override_by: Optional[int] = Field(None, description="User ID who overrode completion")
    tracked: bool = Field(True, description="Whether completion is tracked")
    value: Optional[int] = Field(None, description="Completion value")
    grade: Optional[float] = Field(None, description="Grade value")
    passgrade: Optional[float] = Field(None, description="Passing grade")
    has_completion: bool = Field(False, description="Has completion tracking")
    is_automatic: bool = Field(False, description="Automatic completion")
    is_manual: bool = Field(False, description="Manual completion")


class ActivityGrades(BaseModel):
    """Activity grade information."""
    activity_id: int = Field(..., description="Activity instance ID")
    activity_type: str = Field(..., description="Activity type")
    grades: List[Dict[str, Any]] = Field(default_factory=list, description="Grade data")
    maxgrade: Optional[float] = Field(None, description="Maximum grade")
    gradepass: Optional[float] = Field(None, description="Passing grade")
    average: Optional[float] = Field(None, description="Average grade")
    median: Optional[float] = Field(None, description="Median grade")


class ActivityAttempt(BaseModel):
    """User attempt on an activity."""
    id: int = Field(..., description="Attempt ID")
    activity_id: int = Field(..., description="Activity instance ID")
    activity_type: str = Field(..., description="Activity type")
    user_id: int = Field(..., description="User ID")
    attempt_number: int = Field(1, description="Attempt number")
    time_start: Optional[int] = Field(None, description="Start timestamp")
    time_finish: Optional[int] = Field(None, description="Finish timestamp")
    status: str = Field("inprogress", description="Attempt status")
    score: Optional[float] = Field(None, description="Score achieved")
    maxscore: Optional[float] = Field(None, description="Maximum possible score")
    percentage: Optional[float] = Field(None, description="Percentage score")
    feedback: Optional[str] = Field(None, description="Feedback text")
    duration: Optional[int] = Field(None, description="Duration in seconds")


class ActivitySettings(BaseModel):
    """Settings for updating an activity."""
    name: Optional[str] = Field(None, description="Activity name")
    description: Optional[str] = Field(None, description="Activity description")
    visible: Optional[bool] = Field(None, description="Visibility")
    completion: Optional[int] = Field(None, description="Completion tracking")
    completionexpected: Optional[int] = Field(None, description="Expected completion time")
    grade: Optional[float] = Field(None, description="Grade to pass")
    availability: Optional[str] = Field(None, description="Availability conditions")
    # Activity-specific settings can be added as needed


class AssignmentDetails(BaseModel):
    """Assignment-specific details."""
    allowsubmissionsfromdate: Optional[int] = None
    duedate: Optional[int] = None
    cutoffdate: Optional[int] = None
    gradingduedate: Optional[int] = None
    maxattempts: Optional[int] = None
    submissionattachments: Optional[bool] = None
    teamsubmission: Optional[bool] = None
    requireallteammemberssubmit: Optional[bool] = None


class QuizDetails(BaseModel):
    """Quiz-specific details."""
    timelimit: Optional[int] = None
    attemptlimit: Optional[int] = None
    grademethod: Optional[int] = None
    questionsperpage: Optional[int] = None
    shuffleanswers: Optional[bool] = None
    preferredbehaviour: Optional[str] = None
    canredoquestions: Optional[bool] = None
    allowofflineattempts: Optional[bool] = None


class SCORMDetails(BaseModel):
    """SCORM-specific details."""
    version: Optional[str] = None
    maxattempt: Optional[int] = None
    grademethod: Optional[int] = None
    whatgrade: Optional[int] = None
    maxgrade: Optional[int] = None
    packagesize: Optional[int] = None
    packageurl: Optional[str] = None


class H5PDetails(BaseModel):
    """H5P-specific details."""
    displayoptions: Optional[int] = None
    enabletracking: Optional[bool] = None
    grademethod: Optional[int] = None
    content: Optional[Dict[str, Any]] = None


class ForumDetails(BaseModel):
    """Forum-specific details."""
    type: Optional[str] = None
    maxattachments: Optional[int] = None
    maxsubscriptions: Optional[int] = None
    trackreadposts: Optional[bool] = None
    displaywordcount: Optional[bool] = None
    lockdiscussionafter: Optional[int] = None


class ResourceDetails(BaseModel):
    """Resource-specific details."""
    display: Optional[int] = None
    showexpanded: Optional[bool] = None
    popupwidth: Optional[int] = None
    popupheight: Optional[int] = None
    filterfiles: Optional[int] = None


class FolderDetails(BaseModel):
    """Folder-specific details."""
    showexpanded: Optional[bool] = None
    display: Optional[int] = None


class PageDetails(BaseModel):
    """Page-specific details."""
    display: Optional[int] = None
    displayoptions: Optional[str] = None
    content: Optional[str] = None
    contentformat: Optional[int] = None


class URLDetails(BaseModel):
    """URL-specific details."""
    externalurl: Optional[str] = None
    display: Optional[int] = None
    popupwidth: Optional[int] = None
    popupheight: Optional[int] = None


class LessonDetails(BaseModel):
    """Lesson-specific details."""
    practice: Optional[bool] = None
    modattempts: Optional[bool] = None
    review: Optional[bool] = None
    maxattempts: Optional[int] = None
    retake: Optional[bool] = None
    usepassword: Optional[bool] = None
    password: Optional[str] = None


class GlossaryDetails(BaseModel):
    """Glossary-specific details."""
    displayformat: Optional[str] = None
    approvaldisplayformat: Optional[str] = None
    showall: Optional[bool] = None
    showalphabet: Optional[bool] = None
    showspecial: Optional[bool] = None
    allowduplicatedentries: Optional[bool] = None


class DatabaseDetails(BaseModel):
    """Database-specific details."""
    requiredentries: Optional[int] = None
    requiredentriestoview: Optional[int] = None
    maxentries: Optional[int] = None
    comments: Optional[bool] = None
    approvalrequired: Optional[bool] = None
    defaultsort: Optional[int] = None


class WorkshopDetails(BaseModel):
    """Workshop-specific details."""
    strategy: Optional[str] = None
    grade: Optional[int] = None
    gradingrade: Optional[int] = None
    submissiongrade: Optional[int] = None
    submissionstart: Optional[int] = None
    submissionend: Optional[int] = None
    assessmentstart: Optional[int] = None
    assessmentend: Optional[int] = None


class ChatDetails(BaseModel):
    """Chat-specific details."""
    chattime: Optional[int] = None
    schedule: Optional[int] = None
    keepdays: Optional[int] = None
    studentlogs: Optional[int] = None


class ChoiceDetails(BaseModel):
    """Choice-specific details."""
    limitanswers: Optional[bool] = None
    showunanswered: Optional[bool] = None
    showresults: Optional[int] = None
    publish: Optional[bool] = None
    allowmultiple: Optional[bool] = None
    allowupdate: Optional[bool] = None
    timemakechoice: Optional[int] = None


class FeedbackDetails(BaseModel):
    """Feedback-specific details."""
    anonymous: Optional[int] = None
    emailnotification: Optional[bool] = None
    multiple_submit: Optional[bool] = None
    autonumbering: Optional[bool] = None
    site_after_submit: Optional[str] = None
    page_after_submit: Optional[str] = None


class ActivityDetail(BaseModel):
    """Complete activity detail with type-specific information."""
    id: int = Field(..., description="Course module ID")
    course_id: int = Field(..., description="Course ID")
    name: str = Field(..., description="Activity name")
    modname: str = Field(..., description="Module type")
    instance: int = Field(..., description="Instance ID")
    description: str = Field("", description="Activity description")
    visible: int = Field(1, description="Visibility")
    section_id: int = Field(0, description="Section ID")
    section_number: int = Field(0, description="Section number")
    section_name: str = Field("", description="Section name")
    completion: int = Field(0, description="Completion tracking")
    completionexpected: Optional[int] = Field(None, description="Expected completion")
    contents: List[ActivityContent] = Field(default_factory=list, description="Activity contents")
    
    # Type-specific details (only one will be populated based on modname)
    assignment_details: Optional[AssignmentDetails] = None
    quiz_details: Optional[QuizDetails] = None
    scorm_details: Optional[SCORMDetails] = None
    h5p_details: Optional[H5PDetails] = None
    forum_details: Optional[ForumDetails] = None
    resource_details: Optional[ResourceDetails] = None
    folder_details: Optional[FolderDetails] = None
    page_details: Optional[PageDetails] = None
    url_details: Optional[URLDetails] = None
    lesson_details: Optional[LessonDetails] = None
    glossary_details: Optional[GlossaryDetails] = None
    database_details: Optional[DatabaseDetails] = None
    workshop_details: Optional[WorkshopDetails] = None
    chat_details: Optional[ChatDetails] = None
    choice_details: Optional[ChoiceDetails] = None
    feedback_details: Optional[FeedbackDetails] = None


class SectionContent(BaseModel):
    """Content summary for a section."""
    id: int = Field(..., description="Section ID")
    number: int = Field(..., description="Section number")
    name: str = Field("", description="Section name")
    activities: List[Activity] = Field(default_factory=list, description="Activities in section")
    activity_count: int = Field(0, description="Number of activities")
    
    def model_post_init(self, __context) -> None:
        """Calculate activity count after init."""
        self.activity_count = len(self.activities)


class CourseContent(BaseModel):
    """Complete course content summary."""
    course_id: int = Field(..., description="Course ID")
    total_activities: int = Field(0, description="Total number of activities")
    total_sections: int = Field(0, description="Total number of sections")
    sections: List[SectionContent] = Field(default_factory=list, description="Sections with activities")
    activity_types: Dict[str, int] = Field(default_factory=dict, description="Count by activity type")
    completion_tracking_enabled: bool = Field(False, description="Whether completion tracking is enabled")