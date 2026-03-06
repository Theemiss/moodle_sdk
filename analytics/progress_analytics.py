"""Progress and completion analytics."""

import numpy as np
from typing import Dict, List
from collections import defaultdict

from schemas.progress import (
    ActivityCompletion,
    CompletionStatus,
    UserProgress,
)


def compute_completion_rate(completions: List[CompletionStatus]) -> float:
    """
    Compute overall completion rate from list of completion statuses.

    Args:
        completions: List of completion statuses

    Returns:
        Completion rate (0-1)
    """
    if not completions:
        return 0.0

    completed = sum(1 for c in completions if c.completed)
    return completed / len(completions)


def compute_activity_engagement_score(completions: List[ActivityCompletion]) -> float:
    """
    Compute engagement score based on activity completion patterns.

    Args:
        completions: List of activity completions

    Returns:
        Engagement score (0-100)
    """
    if not completions:
        return 0.0

    # Tracked vs total
    tracked = [c for c in completions if c.tracked]
    if not tracked:
        return 0.0

    # Completion score (weighted)
    completion_states = [c.state for c in tracked]
    weighted_sum = 0

    # State 2 (complete pass) = 100%
    # State 1 (complete) = 75%
    # State 3 (complete fail) = 25%
    # State 0 (incomplete) = 0%

    for state in completion_states:
        if state == 2:
            weighted_sum += 100
        elif state == 1:
            weighted_sum += 75
        elif state == 3:
            weighted_sum += 25
        # state 0 adds 0

    return weighted_sum / len(completion_states)


def get_at_risk_users(
    progress_list: List[UserProgress],
    threshold: float = 0.3,
    min_activities: int = 5,
) -> List[int]:
    """
    Identify users at risk based on low progress.

    Args:
        progress_list: List of user progress objects
        threshold: Completion percentage threshold (default 30%)
        min_activities: Minimum activities to consider (to filter empty courses)

    Returns:
        List of user IDs at risk
    """
    at_risk = []

    for progress in progress_list:
        # Check each course
        at_risk_in_any = False

        for course_id, completion in progress.course_completions.items():
            if completion.total_activities >= min_activities:
                if completion.completion_percentage < (threshold * 100):
                    at_risk_in_any = True
                    break

        if at_risk_in_any:
            at_risk.append(progress.user_id)

    return at_risk


def compute_cohort_progress_metrics(progress_list: List[UserProgress]) -> Dict[str, float]:
    """
    Compute aggregate progress metrics for a cohort.

    Args:
        progress_list: List of user progress objects

    Returns:
        Dictionary of cohort metrics
    """
    if not progress_list:
        return {
            "avg_completion_rate": 0,
            "median_completion_rate": 0,
            "std_dev_completion": 0,
            "completion_rate_by_course": {},
            "at_risk_percentage": 0,
        }

    # Average overall completion
    completions = [p.overall_completion_percentage for p in progress_list]

    # Completion by course
    course_completions = defaultdict(list)
    for progress in progress_list:
        for course_id, completion in progress.course_completions.items():
            course_completions[course_id].append(completion.completion_percentage)

    completion_by_course = {}
    for course_id, percs in course_completions.items():
        completion_by_course[str(course_id)] = np.mean(percs)

    # At risk percentage
    at_risk = get_at_risk_users(progress_list)
    at_risk_pct = len(at_risk) / len(progress_list) if progress_list else 0

    return {
        "avg_completion_rate": float(np.mean(completions)),
        "median_completion_rate": float(np.median(completions)),
        "std_dev_completion": float(np.std(completions)),
        "completion_rate_by_course": completion_by_course,
        "at_risk_percentage": at_risk_pct,
    }