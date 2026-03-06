"""Grade management CLI commands."""

import asyncio
import csv
import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.bar import Bar
from rich.text import Text

from client.moodle_client import AsyncMoodleClient
from services.grade_service import GradeService
from analytics.grade_analytics import (
    compute_grade_distribution,
    compute_student_performance,
)
from cli.output import print_error

app = typer.Typer(help="Grade management commands")
console = Console()


@app.command("report")
def grade_report(
    course_id: int = typer.Argument(..., help="Course ID"),
    user_id: Optional[int] = typer.Option(None, "--user-id", "-u", help="Specific user ID"),
    format: str = typer.Option("table", "--format", help="Output format (table, json, csv)"),
) -> None:
    """Get grade report for a course or specific user."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = GradeService(client)

            try:
                if user_id:
                    # Single user report
                    report = await service.get_user_grades(user_id, course_id)

                    if format == "json":
                        console.print_json(data=json.dumps(report.model_dump()))
                    elif format == "csv":
                        writer = csv.writer(sys.stdout)
                        writer.writerow(["Grade Item", "Grade", "Percentage", "Letter Grade"])
                        for grade in report.grades:
                            grade_item = next(
                                (g for g in report.grade_items if g.id == grade.grade_item_id),
                                None,
                            )
                            item_name = grade_item.itemname if grade_item else "Unknown"
                            writer.writerow([
                                item_name,
                                grade.grade,
                                grade.percentage,
                                grade.lettergrade,
                            ])
                    else:
                        console.print(f"[bold]Grade Report for {report.user_fullname} - Course {course_id}[/]")
                        table = Table()
                        table.add_column("Grade Item")
                        table.add_column("Grade", justify="right")
                        table.add_column("Percentage", justify="right")
                        table.add_column("Letter", justify="center")

                        for grade in report.grades:
                            grade_item = next(
                                (g for g in report.grade_items if g.id == grade.grade_item_id),
                                None,
                            )
                            item_name = grade_item.itemname if grade_item else "Unknown"
                            table.add_row(
                                item_name,
                                str(grade.grade) if grade.grade else "-",
                                f"{grade.percentage:.1f}%" if grade.percentage else "-",
                                grade.lettergrade or "-",
                            )

                        console.print(table)

                        if report.total_grade:
                            console.print(f"\n[bold]Total Grade:[/] {report.total_grade}")

                else:
                    # Full course report
                    reports = await service.get_course_grades(course_id)

                    if format == "json":
                        data = [r.model_dump() for r in reports]
                        console.print_json(data=json.dumps(data))
                    elif format == "csv":
                        writer = csv.writer(sys.stdout)
                        writer.writerow(["User ID", "User Name", "Grade", "Percentage"])
                        for r in reports:
                            if r.total_percentage:
                                writer.writerow([
                                    r.user_id,
                                    r.user_fullname,
                                    r.total_grade,
                                    f"{r.total_percentage:.1f}%",
                                ])
                    else:
                        table = Table(title=f"Grade Report - Course {course_id}")
                        table.add_column("User ID", style="cyan")
                        table.add_column("User Name")
                        table.add_column("Grade", justify="right")
                        table.add_column("Percentage", justify="right")

                        for r in reports:
                            if r.total_grade:
                                table.add_row(
                                    str(r.user_id),
                                    r.user_fullname,
                                    str(r.total_grade),
                                    f"{r.total_percentage:.1f}%" if r.total_percentage else "-",
                                )

                        console.print(table)

            except Exception as e:
                print_error(f"Failed to get grade report: {e}")

    asyncio.run(_run())


@app.command("distribution")
def grade_distribution(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Show grade distribution statistics for a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = GradeService(client)

            try:
                reports = await service.get_course_grades(course_id)
                distribution = compute_grade_distribution(reports)

                if format == "json":
                    console.print_json(data=json.dumps(distribution.model_dump()))
                else:
                    console.print(f"[bold]Grade Distribution - Course {course_id}[/]")
                    console.print(f"Total Students: {distribution.total_students}")
                    console.print(f"Mean: {distribution.mean:.2f}%")
                    console.print(f"Median: {distribution.median:.2f}%")
                    console.print(f"Std Dev: {distribution.std_dev:.2f}")
                    console.print(f"Pass Rate: {distribution.pass_rate * 100:.1f}%")

                    console.print("\n[bold]Percentiles:[/]")
                    for p, value in distribution.percentiles.items():
                        console.print(f"  {p}th: {value:.1f}%")

                    console.print("\n[bold]Grade Distribution:[/]")
                    for bucket, count in distribution.grade_buckets.items():
                        percentage = (count / distribution.total_students * 100) if distribution.total_students > 0 else 0
                        bar = Bar(
                            size=int(percentage),
                            maximum=100,
                            width=30,
                        )
                        console.print(f"  {bucket}: {bar} {count} ({percentage:.1f}%)")

            except Exception as e:
                print_error(f"Failed to compute grade distribution: {e}")

    asyncio.run(_run())


@app.command("performance")
def student_performance(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Show ranked student performance with analytics."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = GradeService(client)

            try:
                reports = await service.get_course_grades(course_id)
                performances = compute_student_performance(reports)

                if format == "json":
                    data = [p.model_dump() for p in performances]
                    console.print_json(data=json.dumps(data))
                else:
                    table = Table(title=f"Student Performance - Course {course_id}")
                    table.add_column("Rank", justify="right", style="cyan")
                    table.add_column("Student")
                    table.add_column("Grade", justify="right")
                    table.add_column("Z-Score", justify="right")
                    table.add_column("Percentile", justify="right")
                    table.add_column("Band", justify="center")

                    for idx, p in enumerate(performances, 1):
                        band_style = {
                            "A": "green",
                            "B": "cyan",
                            "C": "yellow",
                            "D": "orange3",
                            "F": "red",
                        }.get(p.performance_band, "white")

                        table.add_row(
                            str(idx),
                            p.user_fullname,
                            f"{p.grade:.1f}%",
                            f"{p.z_score:.2f}",
                            f"{p.percentile_rank:.1f}%",
                            f"[{band_style}]{p.performance_band}[/]",
                        )

                    console.print(table)

            except Exception as e:
                print_error(f"Failed to analyze performance: {e}")

    asyncio.run(_run())