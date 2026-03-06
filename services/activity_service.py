"""Activity log service for tracking user actions."""

import logging
from datetime import datetime
from typing import List, Optional

from client.moodle_client import AsyncMoodleClient
from schemas.activity import ActivityLog

logger = logging.getLogger(__name__)


class ActivityService:
    """Service for activity log operations."""

    def __init__(self, client: AsyncMoodleClient) -> None:
        self.client = client

    async def get_course_logs(
        self,
        course_id: int,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[ActivityLog]:
        """
        Get activity logs for a course.
        
        Args:
            course_id: Course ID
            since: Only get logs after this date
            limit: Maximum number of logs to return
            
        Returns:
            List of activity logs
        """
        # Note: Moodle's core_course_get_logs requires different parameters
        # This is a simplified version - you may need to adjust based on your Moodle version
        
        params = {
            "courseid": course_id,
            "limit": limit,
        }
        
        if since:
            params["since"] = int(since.timestamp())
        
        try:
            response = await self.client.call("core_course_get_logs", params)
            
            logs = []
            for log_data in response.get("logs", []):
                # Convert timestamp to datetime
                timecreated = None
                if log_data.get("time"):
                    try:
                        timecreated = datetime.fromtimestamp(int(log_data["time"]))
                    except (ValueError, TypeError):
                        pass
                
                log = ActivityLog(
                    id=log_data.get("id", 0),
                    user_id=log_data.get("userid", 0),
                    course_id=log_data.get("courseid", course_id),
                    timecreated=timecreated,
                    event_name=log_data.get("eventname", ""),
                    component=log_data.get("component", ""),
                    action=log_data.get("action", ""),
                    target=log_data.get("target", ""),
                    object_table=log_data.get("objecttable"),
                    object_id=log_data.get("objectid"),
                    ip=log_data.get("ip"),
                )
                logs.append(log)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get course logs: {e}")
            return []

    async def get_user_logs(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[ActivityLog]:
        """
        Get activity logs for a specific user.
        
        Args:
            user_id: User ID
            course_id: Optional course ID to filter by
            since: Only get logs after this date
            limit: Maximum number of logs to return
            
        Returns:
            List of activity logs
        """
        params = {
            "userid": user_id,
            "limit": limit,
        }
        
        if course_id:
            params["courseid"] = course_id
        
        if since:
            params["since"] = int(since.timestamp())
        
        try:
            response = await self.client.call("core_user_get_user_logs", params)
            
            logs = []
            for log_data in response.get("logs", []):
                timecreated = None
                if log_data.get("time"):
                    try:
                        timecreated = datetime.fromtimestamp(int(log_data["time"]))
                    except (ValueError, TypeError):
                        pass
                
                log = ActivityLog(
                    id=log_data.get("id", 0),
                    user_id=user_id,
                    course_id=log_data.get("courseid", 0),
                    timecreated=timecreated,
                    event_name=log_data.get("eventname", ""),
                    component=log_data.get("component", ""),
                    action=log_data.get("action", ""),
                    target=log_data.get("target", ""),
                    object_table=log_data.get("objecttable"),
                    object_id=log_data.get("objectid"),
                    ip=log_data.get("ip"),
                )
                logs.append(log)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get user logs: {e}")
            return []