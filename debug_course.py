#!/usr/bin/env python3
"""Debug script for course retrieval."""

import asyncio
import json
import sys
from client.moodle_client import AsyncMoodleClient
from config.settings import settings

async def debug_course(course_id):
    print(f"\n🔍 Debugging course ID: {course_id}")
    print(f"🌐 Moodle URL: {settings.moodle_url}")
    print(f"🔑 Token exists: {bool(settings.moodle_token)}")
    print(f"📦 Service: {settings.moodle_service_name}")
    
    async with AsyncMoodleClient() as client:
        # Method 1: Get all courses and filter
        print("\n📋 Method 1: Get all courses and filter")
        try:
            all_courses = await client.call("core_course_get_courses", {})
            print(f"   Got {len(all_courses)} total courses")
            
            found = None
            for course in all_courses:
                if course.get('id') == course_id:
                    found = course
                    print(f"   ✅ Found: {course.get('fullname')} (ID: {course.get('id')})")
                    print(f"   Short name: {course.get('shortname')}")
                    print(f"   Category: {course.get('categoryid')}")
                    break
            
            if not found:
                print(f"   ❌ Course {course_id} not found in list")
                print(f"   Available IDs: {[c.get('id') for c in all_courses]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Method 2: Try different parameter formats
        print("\n🔧 Method 2: Try different parameter formats")
        param_formats = [
            ("options", {"options": {"ids": [course_id]}}),
            ("courseids", {"courseids": [course_id]}),
            ("id", {"id": course_id}),
            ("ids", {"ids": [course_id]}),
        ]
        
        for name, params in param_formats:
            try:
                print(f"   Trying {name}...")
                response = await client.call("core_course_get_courses", params)
                if response:
                    print(f"   ✅ Success with {name}: {response}")
                else:
                    print(f"   ⚠️  Empty response with {name}")
            except Exception as e:
                print(f"   ❌ {name} failed: {e}")
        
        # Method 3: Try alternative function
        print("\n🔧 Method 3: Try core_course_get_course_by_id")
        try:
            response = await client.call(
                "core_course_get_course_by_id",
                {"courseid": course_id}
            )
            print(f"   ✅ Success: {response}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    course_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    asyncio.run(debug_course(course_id))
