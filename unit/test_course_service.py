"""Unit tests for CourseService."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from client.exceptions import MoodleNotFoundError
from client.moodle_client import AsyncMoodleClient
from services.course_service import CourseService
from schemas.course import CourseCreate, CourseUpdate


@pytest.fixture
def mock_client():
    """Create a mock Moodle client."""
    client = Mock(spec=AsyncMoodleClient)
    client.call = AsyncMock()
    return client


@pytest.fixture
def course_service(mock_client):
    """Create a CourseService with mock client."""
    return CourseService(mock_client)


@pytest.mark.asyncio
async def test_list_courses(course_service, mock_client):
    """Test listing all courses."""
    # Mock response
    mock_response = [
        {
            "id": 1,
            "shortname": "CS101",
            "fullname": "Computer Science 101",
            "categoryid": 1,
            "visible": 1,
        }
    ]
    mock_client.call.return_value = mock_response

    # Call service
    courses = await course_service.list_courses()

    # Assertions
    mock_client.call.assert_called_once_with("core_course_get_courses", {})
    assert len(courses) == 1
    assert courses[0].id == 1
    assert courses[0].shortname == "CS101"
    assert courses[0].fullname == "Computer Science 101"
    assert courses[0].categoryid == 1
    assert courses[0].visible == 1


@pytest.mark.asyncio
async def test_list_courses_with_category(course_service, mock_client):
    """Test listing courses filtered by category."""
    mock_client.call.return_value = []

    await course_service.list_courses(category_id=5)

    mock_client.call.assert_called_once_with(
        "core_course_get_courses",
        {"criteria": [{"key": "category", "value": 5}]},
    )


@pytest.mark.asyncio
async def test_get_course_success(course_service, mock_client):
    """Test getting a single course by ID."""
    mock_response = [
        {
            "id": 42,
            "shortname": "TEST101",
            "fullname": "Test Course",
            "categoryid": 2,
            "visible": 1,
        }
    ]
    mock_client.call.return_value = mock_response

    course = await course_service.get_course(42)

    mock_client.call.assert_called_once_with(
        "core_course_get_courses",
        {"options": {"ids": [42]}},
    )
    assert course.id == 42
    assert course.shortname == "TEST101"


@pytest.mark.asyncio
async def test_get_course_not_found(course_service, mock_client):
    """Test getting a non-existent course raises error."""
    mock_client.call.return_value = []

    with pytest.raises(MoodleNotFoundError) as exc_info:
        await course_service.get_course(999)

    assert "Course" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_course(course_service, mock_client):
    """Test creating a new course."""
    # Mock responses
    mock_client.call.side_effect = [
        [{"id": 100}],  # First call: create response
        [{"id": 100, "shortname": "NEW101", "fullname": "New Course", "categoryid": 1, "visible": 1}],  # Second call: get course
    ]

    course_data = CourseCreate(
        shortname="NEW101",
        fullname="New Course",
        categoryid=1,
    )

    course = await course_service.create_course(course_data)

    assert course.id == 100
    assert course.shortname == "NEW101"
    assert mock_client.call.call_count == 2


@pytest.mark.asyncio
async def test_update_course(course_service, mock_client):
    """Test updating a course."""
    # Mock get course after update
    mock_client.call.side_effect = [
        None,  # Update call
        [{"id": 1, "shortname": "CS101", "fullname": "Updated Name", "categoryid": 1, "visible": 1}],  # Get call
    ]

    update_data = CourseUpdate(fullname="Updated Name")
    course = await course_service.update_course(1, update_data)

    assert course.fullname == "Updated Name"

    # Verify update call had correct params
    update_call = mock_client.call.call_args_list[0]
    assert update_call[0][0] == "core_course_update_courses"
    assert update_call[0][1]["courses"][0]["id"] == 1
    assert update_call[0][1]["courses"][0]["fullname"] == "Updated Name"


@pytest.mark.asyncio
async def test_duplicate_course(course_service, mock_client):
    """Test duplicating a course."""
    mock_client.call.side_effect = [
        {"id": 101},  # Duplicate response
        [{"id": 101, "shortname": "COPY101", "fullname": "Copy of Course", "categoryid": 1, "visible": 1}],  # Get call
    ]

    course = await course_service.duplicate_course(
        1,
        "COPY101",
        "Copy of Course",
    )

    assert course.id == 101
    assert course.shortname == "COPY101"

    duplicate_call = mock_client.call.call_args_list[0]
    assert duplicate_call[0][0] == "core_course_duplicate_course"
    assert duplicate_call[0][1]["courseid"] == 1
    assert duplicate_call[0][1]["shortname"] == "COPY101"


@pytest.mark.asyncio
async def test_archive_course(course_service, mock_client):
    """Test archiving a course."""
    # Mock get course
    mock_client.call.side_effect = [
        [{"id": 1, "shortname": "CS101", "fullname": "Course", "categoryid": 1, "visible": 1}],  # Get call
        None,  # Update call
    ]

    result = await course_service.archive_course(1, archive_category_id=99)

    assert result is True

    # Verify update set visible=0 and changed category
    update_call = mock_client.call.call_args_list[1]
    assert update_call[0][1]["courses"][0]["id"] == 1
    assert update_call[0][1]["courses"][0]["visible"] == 0
    assert update_call[0][1]["courses"][0]["categoryid"] == 99


@pytest.mark.asyncio
async def test_get_course_structure(course_service, mock_client):
    """Test getting course structure."""
    mock_response = [
        {
            "id": 1,
            "name": "Section 1",
            "section": 0,
            "visible": 1,
            "modules": [
                {
                    "id": 10,
                    "name": "Assignment 1",
                    "modname": "assign",
                    "instance": 100,
                    "visible": 1,
                }
            ],
        }
    ]
    mock_client.call.return_value = mock_response

    structure = await course_service.get_course_structure(1)

    assert structure.course_id == 1
    assert len(structure.sections) == 1
    assert structure.sections[0].name == "Section 1"
    assert len(structure.sections[0].modules) == 1
    assert structure.sections[0].modules[0].name == "Assignment 1"
    assert structure.sections[0].modules[0].modname == "assign"