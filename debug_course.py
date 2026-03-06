import asyncio
import json
from client.moodle_client import AsyncMoodleClient
from config.settings import settings

async def debug_course(course_id):
    print(f"Debugging course ID: {course_id}")
    print(f"Moodle URL: {settings.moodle_url}")
    
    async with AsyncMoodleClient() as client:
        # First, try to get all courses to see what's returned
        print("\n1. Getting all courses...")
        all_courses = await client.call("core_course_get_courses", {})
        print(f"   Got {len(all_courses)} courses")
        
        # Find our course in the list
        found = None
        for course in all_courses:
            if course.get('id') == course_id:
                found = course
                print(f"   ✓ Found course in list: {course.get('fullname')}")
                break
        
        if not found:
            print(f"   ✗ Course {course_id} not found in the list!")
        
        # Now try to get specifically by ID
        print(f"\n2. Getting course specifically by ID {course_id}...")
        try:
            specific = await client.call(
                "core_course_get_courses", 
                {"options": {"ids": [course_id]}}
            )
            print(f"   Response: {json.dumps(specific, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")

asyncio.run(debug_course(4))
