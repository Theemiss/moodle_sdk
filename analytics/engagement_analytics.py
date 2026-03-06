"""Engagement analytics module."""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, Counter

from schemas.activity import ActivityLog, EngagementMetric


class EngagementAnalytics:
    """Analytics for user engagement."""

    def __init__(self, logs: List[ActivityLog]):
        self.logs = logs

    def compute_user_engagement_score(self, user_id: int) -> float:
        """
        Compute overall engagement score for a user.

        Score factors:
        - Activity frequency (50%)
        - Activity recency (30%)
        - Activity diversity (20%)

        Args:
            user_id: User ID

        Returns:
            Engagement score (0-100)
        """
        user_logs = [log for log in self.logs if log.user_id == user_id]

        if not user_logs:
            return 0.0

        # Activity frequency score
        now = datetime.now()
        log_times = [log.timecreated for log in user_logs]

        # Calculate days with activity
        days_active = len(set(log.date() for log in user_logs))
        max_days = 30  # Look at last 30 days
        frequency_score = min(100, (days_active / max_days) * 100)

        # Recency score
        if log_times:
            most_recent = max(log_times)
            days_since = (now - most_recent).days
            recency_score = max(0, 100 - (days_since * 10))  # Decay 10 points per day
        else:
            recency_score = 0

        # Diversity score (different activity types)
        activity_types = set(log.event_name for log in user_logs)
        max_types = 20  # Expected max different activity types
        diversity_score = min(100, (len(activity_types) / max_types) * 100)

        # Weighted combination
        total_score = (
            frequency_score * 0.5 +
            recency_score * 0.3 +
            diversity_score * 0.2
        )

        return min(100, total_score)

    def get_activity_hotspots(self, course_id: int) -> List[Dict[str, any]]:
        """
        Identify most active areas in a course.

        Args:
            course_id: Course ID

        Returns:
            List of activity hotspots with engagement counts
        """
        course_logs = [log for log in self.logs if log.course_id == course_id]

        activity_counts = defaultdict(int)
        activity_last_access = {}

        for log in course_logs:
            if log.context_instance_id:
                activity_counts[log.context_instance_id] += 1
                activity_last_access[log.context_instance_id] = max(
                    activity_last_access.get(log.context_instance_id, log.timecreated),
                    log.timecreated,
                )

        hotspots = []
        for activity_id, count in activity_counts.items():
            hotspots.append({
                "activity_id": activity_id,
                "access_count": count,
                "last_access": activity_last_access[activity_id],
                "engagement_score": min(100, (count / 10) * 100),  # Normalize
            })

        # Sort by access count descending
        hotspots.sort(key=lambda x: x["access_count"], reverse=True)
        return hotspots[:10]  # Return top 10

    def compute_cohort_engagement_trends(
        self,
        user_ids: List[int],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, any]:
        """
        Compute engagement trends for a cohort over time.

        Args:
            user_ids: List of user IDs
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Engagement trend metrics
        """
        # Filter logs
        cohort_logs = [
            log for log in self.logs
            if log.user_id in user_ids
            and start_date <= log.timecreated <= end_date
        ]

        if not cohort_logs:
            return {
                "total_actions": 0,
                "daily_average": 0,
                "most_active_day": None,
                "activity_by_type": {},
                "engagement_trend": [],
            }

        # Group by day
        daily_counts = defaultdict(int)
        for log in cohort_logs:
            day_key = log.timecreated.date()
            daily_counts[day_key] += 1

        # Activity by type
        type_counts = Counter(log.event_name for log in cohort_logs)

        # Daily trend (last 30 days)
        trend = []
        current = start_date
        while current <= end_date:
            day_key = current.date()
            trend.append({
                "date": current.isoformat(),
                "count": daily_counts.get(day_key, 0),
            })
            current += timedelta(days=1)

        return {
            "total_actions": len(cohort_logs),
            "daily_average": len(cohort_logs) / max(1, (end_date - start_date).days),
            "most_active_day": max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else None,
            "activity_by_type": dict(type_counts.most_common(10)),
            "engagement_trend": trend,
        }