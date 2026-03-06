"""Admin management service using only real Moodle 5 APIs."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time

from client.moodle_client import AsyncMoodleClient
from schemas.admin import (
    SystemHealth,
    HealthComponent,
    SystemStatus,
    ScheduledTask,
    TaskResult,
)
from client.exceptions import MoodleAPIError

logger = logging.getLogger(__name__)


class AdminService:
    """Service for system administration using only real Moodle 5 APIs."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def check_system_health(self) -> SystemHealth:
        """
        Check overall system health using available APIs.
        
        Returns:
            SystemHealth object with component statuses
        """
        components = []
        warnings = []
        start_time = time.time()
        
        # Check 1: Web Service Availability (core_webservice_get_site_info)
        try:
            ws_start = time.time()
            site_info = await self.client.call("core_webservice_get_site_info", {})
            ws_latency = int((time.time() - ws_start) * 1000)
            
            components.append(HealthComponent(
                name="Web Services",
                status="healthy",
                latency=ws_latency,
                details=f"Version: {site_info.get('version', 'Unknown')}"
            ))
        except Exception as e:
            components.append(HealthComponent(
                name="Web Services",
                status="down",
                details=str(e)
            ))
            warnings.append(f"Web service unavailable: {e}")

        # Check 2: Database (test by fetching a single user)
        try:
            db_start = time.time()
            await self.client.call("core_user_get_users_by_field", {
                "field": "id",
                "values": [2]  # Use a common user ID
            })
            db_latency = int((time.time() - db_start) * 1000)
            
            components.append(HealthComponent(
                name="Database",
                status="healthy",
                latency=db_latency,
                details="Connection successful"
            ))
        except Exception as e:
            components.append(HealthComponent(
                name="Database",
                status="down",
                details=str(e)
            ))
            warnings.append(f"Database connection failed: {e}")

        # Check 3: Course System (test course access)
        try:
            course_start = time.time()
            await self.client.call("core_course_get_courses", {})
            course_latency = int((time.time() - course_start) * 1000)
            
            components.append(HealthComponent(
                name="Course System",
                status="healthy",
                latency=course_latency,
                details="Courses accessible"
            ))
        except Exception as e:
            components.append(HealthComponent(
                name="Course System",
                status="degraded",
                details=str(e)[:50]
            ))

        # Check 4: User System
        try:
            user_start = time.time()
            await self.client.call("core_user_get_users", {
                "criteria": [{"key": "confirmed", "value": 1}]
            })
            user_latency = int((time.time() - user_start) * 1000)
            
            components.append(HealthComponent(
                name="User System",
                status="healthy",
                latency=user_latency,
                details="Users accessible"
            ))
        except Exception as e:
            components.append(HealthComponent(
                name="User System",
                status="degraded",
                details=str(e)[:50]
            ))

        # Determine overall status
        total_time = int((time.time() - start_time) * 1000)
        
        if any(c.status == "down" for c in components):
            overall = "degraded"
        elif all(c.status == "healthy" for c in components):
            overall = "healthy"
        else:
            overall = "degraded"

        return SystemHealth(
            overall_status=overall,
            last_check=datetime.now(),
            response_time=total_time,
            components=components,
            warnings=warnings
        )

    async def get_system_status(self) -> SystemStatus:
        """
        Get system status using available APIs.
        
        Returns:
            SystemStatus object
        """
        # Get site info
        site_info = await self.client.call("core_webservice_get_site_info", {})
        
        # Get user counts
        total_users = 0
        active_users = 0
        
        try:
            users_response = await self.client.call("core_user_get_users", {
                "criteria": [{"key": "confirmed", "value": 1}]
            })
            total_users = len(users_response.get("users", []))
        except Exception as e:
            logger.error(f"Failed to get user count: {e}")
        
        try:
            # Active users (last access in last 30 days)
            thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
            active_response = await self.client.call("core_user_get_users", {
                "criteria": [{"key": "lastaccess", "value": thirty_days_ago}]
            })
            active_users = len(active_response.get("users", []))
        except Exception:
            pass
        
        # Get course counts
        courses = []
        try:
            courses = await self.client.call("core_course_get_courses", {})
        except Exception as e:
            logger.error(f"Failed to get courses: {e}")
        
        total_courses = len(courses)
        active_courses = sum(1 for c in courses if c.get("visible", 1) == 1)
        
        # Get categories
        categories = []
        try:
            categories = await self.client.call("core_course_get_categories", {})
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
        
        total_categories = len(categories)
        
        # Get scheduled tasks for cron info
        last_cron = None
        try:
            tasks = await self.client.call("core_cron_get_scheduled_tasks", {})
            # Find the last run time across all tasks
            for task in tasks:
                last_run = task.get("lastruntime")
                if last_run and (not last_cron or last_run > last_cron):
                    last_cron = last_run
        except Exception:
            pass

        return SystemStatus(
            version=site_info.get("version", ""),
            release=site_info.get("release", ""),
            site_url=site_info.get("siteurl", ""),
            site_name=site_info.get("sitename", ""),
            uptime="Unknown",  # Not available via API
            last_cron=datetime.fromtimestamp(last_cron) if last_cron else None,
            total_users=total_users,
            active_users=active_users,
            total_courses=total_courses,
            active_courses=active_courses,
            total_categories=total_categories,
            disk_usage="Unknown",  # Not available via API
            db_size="Unknown",  # Not available via API
            plugins=[]  # Not available via API
        )

    async def get_scheduled_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ScheduledTask]:
        """
        Get scheduled tasks if available.
        
        Args:
            status: Filter by status
            limit: Maximum number of tasks
            
        Returns:
            List of scheduled tasks or empty list if not available
        """
        try:
            tasks_data = await self.client.call("core_cron_get_scheduled_tasks", {})
            
            tasks = []
            for task in tasks_data[:limit]:
                # Determine status
                if task.get("disabled", False):
                    task_status = "disabled"
                elif task.get("running", False):
                    task_status = "running"
                elif task.get("lastsuccess", True):
                    task_status = "completed"
                else:
                    task_status = "failed"
                
                # Apply status filter
                if status and task_status != status:
                    continue
                
                last_run = task.get("lastruntime")
                next_run = task.get("nextruntime")
                
                tasks.append(ScheduledTask(
                    id=task.get("id", 0),
                    name=task.get("name", ""),
                    type=task.get("type", ""),
                    schedule=task.get("minute", "*") + " " + task.get("hour", "*"),
                    last_run=datetime.fromtimestamp(last_run) if last_run else None,
                    next_run=datetime.fromtimestamp(next_run) if next_run else None,
                    status=task_status,
                    disabled=task.get("disabled", False)
                ))
            
            return tasks
            
        except Exception as e:
            logger.debug(f"Scheduled tasks not available: {e}")
            return []  # Return empty list instead of logging error
        
        
    
    async def run_scheduled_task(self, task_id: int) -> TaskResult:
        """
        Run a specific scheduled task (REAL API: core_cron_run_scheduled_task).
        
        Args:
            task_id: Task ID
            
        Returns:
            TaskResult with execution status
        """
        try:
            start_time = time.time()
            
            result = await self.client.call("core_cron_run_scheduled_task", {
                "taskid": task_id
            })
            
            duration = int((time.time() - start_time) * 1000)
            
            return TaskResult(
                success=True,
                duration=duration,
                output=result.get("message", f"Task {task_id} completed")
            )
        except Exception as e:
            return TaskResult(
                success=False,
                error=str(e)
            )




    async def get_recent_course_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent course activity by checking course and content modification times.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of courses with recent activity
        """
        try:
            courses = await self.client.call("core_course_get_courses", {})
            
            cutoff = int(time.time()) - (days * 24 * 60 * 60)
            recent = []
            
            for course in courses:
                activities = []
                
                # Check course modification
                timemodified = course.get("timemodified")
                if timemodified and timemodified > cutoff:
                    activities.append({
                        "type": "course_update",
                        "time": timemodified,
                        "description": "Course updated"
                    })
                
                # Check course content if possible
                try:
                    contents = await self.client.call("core_course_get_contents", {
                        "courseid": course.get("id")
                    })
                    for section in contents:
                        for module in section.get("modules", []):
                            mod_time = module.get("timemodified")
                            if mod_time and mod_time > cutoff:
                                activities.append({
                                    "type": "module_update",
                                    "time": mod_time,
                                    "description": f"Activity '{module.get('name')}' updated"
                                })
                except Exception:
                    pass
                
                if activities:
                    # Get the most recent activity
                    latest = max(activities, key=lambda x: x["time"])
                    recent.append({
                        "id": course.get("id"),
                        "fullname": course.get("fullname"),
                        "shortname": course.get("shortname"),
                        "timemodified": datetime.fromtimestamp(latest["time"]),
                        "activity": latest["description"],
                        "activities_count": len(activities)
                    })
            
            # Sort by most recent first
            recent.sort(key=lambda x: x["timemodified"], reverse=True)
            return recent
            
        except Exception as e:
            logger.debug(f"Failed to get recent activity: {e}")
            return []





    async def get_course_completion_stats(self, course_id: int) -> Dict[str, Any]:
        """
        Get course completion statistics using available APIs.
        
        Args:
            course_id: Course ID
            
        Returns:
            Completion statistics
        """
        try:
            # Get enrolled users
            users = await self.client.call("core_enrol_get_enrolled_users", {
                "courseid": course_id
            })
            
            total_users = len(users)
            completed = 0
            
            # Check completion for each user (limited to avoid too many calls)
            for user in users[:20]:  # Limit to 20 users for performance
                try:
                    completion = await self.client.call(
                        "core_completion_get_course_completion_status", {
                            "courseid": course_id,
                            "userid": user["id"]
                        }
                    )
                    if completion.get("completionstatus", {}).get("completed"):
                        completed += 1
                except Exception:
                    pass
            
            return {
                "course_id": course_id,
                "total_users": total_users,
                "completed_users": completed,
                "completion_rate": (completed / total_users * 100) if total_users > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get completion stats: {e}")
            return {
                "course_id": course_id,
                "error": str(e)
            }