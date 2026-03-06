"""Transformer functions to convert Moodle API responses to Pydantic models."""

from typing import List, Dict, Any, Optional
from datetime import datetime

from schemas.course import Course, Section, Module
from schemas.content import ModuleInfo


def transform_course(data: Dict[str, Any]) -> Course:
    """
    Transform raw Moodle course data to Course model.
    
    Args:
        data: Raw course data from Moodle API
        
    Returns:
        Course model instance
    """
    # Convert timestamps to datetime objects
    startdate = None
    enddate = None
    timecreated = None
    timemodified = None
    
    if data.get('startdate'):
        try:
            startdate = datetime.fromtimestamp(int(data['startdate']))
        except (ValueError, TypeError):
            pass
    
    if data.get('enddate'):
        try:
            enddate = datetime.fromtimestamp(int(data['enddate']))
        except (ValueError, TypeError):
            pass
    
    if data.get('timecreated'):
        try:
            timecreated = datetime.fromtimestamp(int(data['timecreated']))
        except (ValueError, TypeError):
            pass
    
    if data.get('timemodified'):
        try:
            timemodified = datetime.fromtimestamp(int(data['timemodified']))
        except (ValueError, TypeError):
            pass
    
    return Course(
        id=data.get('id', 0),
        shortname=data.get('shortname', ''),
        fullname=data.get('fullname', ''),
        categoryid=data.get('categoryid', 0),
        idnumber=data.get('idnumber'),
        summary=data.get('summary'),
        summaryformat=data.get('summaryformat', 1),
        format=data.get('format', 'topics'),
        showgrades=data.get('showgrades', 1),
        newsitems=data.get('newsitems', 5),
        startdate=startdate,
        enddate=enddate,
        visible=data.get('visible', 1),
        groupmode=data.get('groupmode', 0),
        groupmodeforce=data.get('groupmodeforce', 0),
        defaultgroupingid=data.get('defaultgroupingid', 0),
        lang=data.get('lang', 'en'),
        calendartype=data.get('calendartype', 'gregorian'),
        theme=data.get('theme'),
        timecreated=timecreated,
        timemodified=timemodified,
        displayname=data.get('displayname'),
        enablecompletion=data.get('enablecompletion', 0),
        completionnotify=data.get('completionnotify', 0),
        cacherev=data.get('cacherev'),
    )


def transform_sections(sections_data: List[Dict[str, Any]]) -> List[Section]:
    """
    Transform raw Moodle course sections data to Section models.
    
    Args:
        sections_data: Raw sections data from Moodle API
        
    Returns:
        List of Section models
    """
    sections = []
    
    for section_data in sections_data:
        modules = []
        
        for module_data in section_data.get('modules', []):
            module = Module(
                id=module_data.get('id', 0),
                name=module_data.get('name', ''),
                instance=module_data.get('instance', 0),
                modname=module_data.get('modname', ''),
                modplural=module_data.get('modplural', ''),
                idnumber=module_data.get('idnumber'),
                completion=module_data.get('completion'),
                visible=module_data.get('visible', 1),
                visibleoncoursepage=module_data.get('visibleoncoursepage'),
                uservisible=module_data.get('uservisible'),
                availabilityinfo=module_data.get('availabilityinfo'),
                indent=module_data.get('indent'),
            )
            modules.append(module)
        
        section = Section(
            id=section_data.get('id', 0),
            name=section_data.get('name'),
            summary=section_data.get('summary'),
            summaryformat=section_data.get('summaryformat', 1),
            section=section_data.get('section', 0),
            visible=section_data.get('visible', 1),
            availabilityinfo=section_data.get('availabilityinfo'),
            modules=modules,
        )
        sections.append(section)
    
    return sections


def transform_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw Moodle user data.
    
    Args:
        user_data: Raw user data from Moodle API
        
    Returns:
        Transformed user dictionary
    """
    # Convert timestamps
    for field in ['firstaccess', 'lastaccess', 'lastlogin', 'currentlogin']:
        if user_data.get(field):
            try:
                user_data[field] = datetime.fromtimestamp(int(user_data[field]))
            except (ValueError, TypeError):
                user_data[field] = None
    
    return user_data


def transform_grade_item(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw grade item data.
    
    Args:
        item_data: Raw grade item data
        
    Returns:
        Transformed grade item dictionary
    """
    # Convert numeric fields
    for field in ['grademax', 'grademin', 'gradepass', 'weight']:
        if item_data.get(field):
            try:
                item_data[field] = float(item_data[field])
            except (ValueError, TypeError):
                pass
    
    return item_data



def transform_module_info(data: Dict[str, Any]) -> ModuleInfo:
    """
    Transform raw module data to ModuleInfo model.
    
    Args:
        data: Raw module data from Moodle API
        
    Returns:
        ModuleInfo model instance
    """
    from schemas.content import ModuleInfo, ActivityContent
    
    # Get course/module data
    cm = data.get("cm", {})
    course = data.get("course", {})
    
    # Transform contents
    contents = []
    for content_data in cm.get("contents", []):
        content = ActivityContent(
            type=content_data.get("type", ""),
            filename=content_data.get("filename", ""),
            fileurl=content_data.get("fileurl", ""),
            filesize=content_data.get("filesize", 0),
            timecreated=content_data.get("timecreated"),
            timemodified=content_data.get("timemodified"),
            mimetype=content_data.get("mimetype"),
            content=content_data.get("content"),
        )
        contents.append(content)
    
    return ModuleInfo(
        id=cm.get("id", 0),
        course_id=course.get("id", 0),
        name=cm.get("name", ""),
        modname=cm.get("modname", ""),
        instance=cm.get("instance", 0),
        description=cm.get("description", ""),
        visible=cm.get("visible", 1),
        section_id=cm.get("section", 0),
        section_number=data.get("section", {}).get("section", 0),
        section_name=data.get("section", {}).get("name", ""),
        completion=cm.get("completion", 0),
        completionexpected=cm.get("completionexpected"),
        contents=contents,
        url=cm.get("url", ""),
    )