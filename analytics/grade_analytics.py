"""Grade analytics and statistical computations."""

import numpy as np
from typing import Dict, List, Tuple
from collections import Counter

from schemas.grade import (
    GradeDistribution,
    GradeReport,
    StudentPerformance,
)


def compute_grade_distribution(grades: List[GradeReport]) -> GradeDistribution:
    """
    Compute statistical distribution of grades.

    Args:
        grades: List of grade reports (one per student)

    Returns:
        Grade distribution statistics
    """
    if not grades:
        return GradeDistribution(
            course_id=0,
            total_students=0,
            mean=0,
            median=0,
            std_dev=0,
            percentiles={},
            pass_rate=0,
            grade_buckets={},
        )

    # Extract percentages
    percentages = []
    passes = 0

    for report in grades:
        if report.total_percentage is not None:
            percentages.append(report.total_percentage)
            if report.total_percentage >= 60:  # Standard pass mark
                passes += 1

    if not percentages:
        percentages = [0]

    # Calculate statistics
    mean = np.mean(percentages)
    median = np.median(percentages)
    std_dev = np.std(percentages)

    # Percentiles
    percentiles = {
        "25": float(np.percentile(percentages, 25)),
        "50": float(np.percentile(percentages, 50)),
        "75": float(np.percentile(percentages, 75)),
        "90": float(np.percentile(percentages, 90)),
    }

    # Grade buckets
    buckets = {
        "A (90-100)": sum(1 for p in percentages if p >= 90),
        "B (80-89)": sum(1 for p in percentages if 80 <= p < 90),
        "C (70-79)": sum(1 for p in percentages if 70 <= p < 80),
        "D (60-69)": sum(1 for p in percentages if 60 <= p < 70),
        "F (0-59)": sum(1 for p in percentages if p < 60),
    }

    course_id = grades[0].course_id if grades else 0

    return GradeDistribution(
        course_id=course_id,
        total_students=len(grades),
        mean=float(mean),
        median=float(median),
        std_dev=float(std_dev),
        percentiles=percentiles,
        pass_rate=passes / len(grades) if grades else 0,
        grade_buckets=buckets,
    )


def compute_student_performance(grades: List[GradeReport]) -> List[StudentPerformance]:
    """
    Compute individual student performance metrics with rankings.

    Args:
        grades: List of grade reports

    Returns:
        List of student performance objects with z-scores and percentiles
    """
    if not grades:
        return []

    # Extract percentages
    percentages = []
    user_grades = []

    for report in grades:
        if report.total_percentage is not None:
            percentages.append(report.total_percentage)
            user_grades.append((report.user_id, report.user_fullname, report.total_percentage))

    if not percentages:
        return []

    # Calculate statistics
    mean = np.mean(percentages)
    std_dev = np.std(percentages)

    performances = []

    for user_id, fullname, grade in user_grades:
        z_score = (grade - mean) / std_dev if std_dev > 0 else 0

        # Percentile rank
        percentile = sum(1 for p in percentages if p < grade) / len(percentages) * 100

        # Performance band
        if grade >= 90:
            band = "A"
        elif grade >= 80:
            band = "B"
        elif grade >= 70:
            band = "C"
        elif grade >= 60:
            band = "D"
        else:
            band = "F"

        performances.append(
            StudentPerformance(
                user_id=user_id,
                user_fullname=fullname,
                grade=grade,
                percentage=grade,
                z_score=float(z_score),
                percentile_rank=float(percentile),
                performance_band=band,
                above_average=grade > mean,
            )
        )

    # Sort by grade descending
    performances.sort(key=lambda x: x.grade, reverse=True)

    return performances


def compare_cohort_grades(
    cohort_a: List[GradeReport], cohort_b: List[GradeReport]
) -> Dict[str, float]:
    """
    Compare grade distributions between two cohorts.

    Args:
        cohort_a: First cohort grade reports
        cohort_b: Second cohort grade reports

    Returns:
        Comparison metrics
    """
    dist_a = compute_grade_distribution(cohort_a)
    dist_b = compute_grade_distribution(cohort_b)

    return {
        "mean_difference": dist_b.mean - dist_a.mean,
        "median_difference": dist_b.median - dist_a.median,
        "pass_rate_difference": dist_b.pass_rate - dist_a.pass_rate,
        "effect_size": (dist_b.mean - dist_a.mean) / np.sqrt(
            (dist_a.std_dev**2 + dist_b.std_dev**2) / 2
        ) if (dist_a.std_dev + dist_b.std_dev) > 0 else 0,
    }