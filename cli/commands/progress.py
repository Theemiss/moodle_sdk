"""Progress tracking CLI commands."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn

from client.moodle_client import AsyncMoodleClient
from services.progress_service import ProgressService
from analytics.progress_analytics import (
    compute_completion_rate,
    get_at_risk_users,
    compute_cohort_progress_metrics,
)
from cli.output import print_error, print_success

app = typer.Typer(help="Progress tracking commands")
console = Console()


@app.command("report")
def progress_report(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: Optional[int] = typer.Option(None, "--course-id", "-c", help="Specific course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get progress report for a user."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ProgressService(client)

            try:
                if course_id:
                    # Single course progress
                    completion = await service.get_course_completion(user_id, course_id)

                    if format == "json":
                        console.print_json(data=json.dumps(completion.model_dump()))
                    else:
                        console.print(f"[bold]Progress Report for User {user_id} - Course {course_id}[/]")

                        # Overall progress bar
                        progress_display = Progress(
                            TextColumn("[progress.description]{task.description}"),
                            BarColumn(),
                            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        )
                        with progress_display:
                            progress_display.add_task(
                                "Course Completion",
                                total=completion.total_activities,
                                completed=completion.activities_completed,
                            )

                        console.print(f"\nStatus: {'[green]Completed[/]' if completion.completed else '[yellow]In Progress[/]'}")
                        if completion.timecompleted:
                            console.print(f"Completed: {completion.timecompleted}")

                        # Activity breakdown
                        if completion.activities:
                            table = Table(title="Activity Completion")
                            table.add_column("Activity")
                            table.add_column("Type")
                            table.add_column("Status", justify="center")
                            table.add_column("Completed", justify="center")

                            for act in completion.activities:
                                status = {
                                    0: "⏳ Incomplete",
                                    1: "✅ Complete",
                                    2: "⭐ Complete (Pass)",
                                    3: "❌ Complete (Fail)",
                                }.get(act.state, "Unknown")

                                completed = act.timecompleted.strftime("%Y-%m-%d") if act.timecompleted else "-"

                                table.add_row(
                                    act.activity_name,
                                    act.activity_type,
                                    status,
                                    completed,
                                )

                            console.print(table)

                else:
                    # Overall user progress
                    progress = await service.get_user_progress(user_id)

                    if format == "json":
                        console.print_json(data=json.dumps(progress.model_dump()))
                    else:
                        console.print(f"[bold]Overall Progress for User {user_id}[/]")

                        # Summary
                        console.print(f"Enrolled Courses: {len(progress.enrolled_courses)}")
                        console.print(f"Completed: {progress.completed_courses}")
                        console.print(f"In Progress: {progress.in_progress_courses}")
                        console.print(f"Overall Completion: {progress.overall_completion_percentage:.1f}%")

                        # Course breakdown
                        if progress.course_completions:
                            table = Table(title="Course Progress")
                            table.add_column("Course ID")
                            table.add_column("Completion %", justify="right")
                            table.add_column("Activities", justify="center")
                            table.add_column("Status")

                            for course_id, completion in progress.course_completions.items():
                                status = "[green]Completed[/]" if completion.completed else "[yellow]In Progress[/]"
                                table.add_row(
                                    str(course_id),
                                    f"{completion.completion_percentage:.1f}%",
                                    f"{completion.activities_completed}/{completion.total_activities}",
                                    status,
                                )

                            console.print(table)

            except Exception as e:
                print_error(f"Failed to get progress report: {e}")

    asyncio.run(_run())


@app.command("completion")
def course_completion(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Show completion statistics for a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            progress_service = ProgressService(client)
            from services.enrollment_service import EnrollmentService
            enrollment_service = EnrollmentService(client)

            try:
                # Get enrolled users
                users = await enrollment_service.list_enrolled_users(course_id)
                user_ids = [u.id for u in users]

                # Get completions
                completions = await progress_service.bulk_get_completions(user_ids, course_id)

                if format == "json":
                    data = [c.model_dump() for c in completions]
                    console.print_json(data=json.dumps(data))
                else:
                    # Calculate statistics
                    completion_rate = compute_completion_rate(completions)

                    console.print(f"[bold]Course Completion - Course {course_id}[/]")
                    console.print(f"Enrolled Users: {len(user_ids)}")
                    console.print(f"Completion Rate: {completion_rate * 100:.1f}%")

                    # Individual completions
                    table = Table(title="User Completion")
                    table.add_column("User ID", style="cyan")
                    table.add_column("User")
                    table.add_column("Status", justify="center")
                    table.add_column("Completion %", justify="right")
                    table.add_column("Activities", justify="center")

                    for completion in completions:
                        user = next((u for u in users if u.id == completion.user_id), None)
                        if user:
                            status = "[green]✓[/]" if completion.completed else "[yellow]⋯[/]"
                            table.add_row(
                                str(completion.user_id),
                                user.fullname,
                                status,
                                f"{completion.completion_percentage:.1f}%",
                                f"{completion.activities_completed}/{completion.total_activities}",
                            )

                    console.print(table)

            except Exception as e:
                print_error(f"Failed to get completion data: {e}")

    asyncio.run(_run())


@app.command("at-risk")
def at_risk_users(
    course_id: int = typer.Argument(..., help="Course ID"),
    threshold: float = typer.Option(0.3, "--threshold", "-t", help="Risk threshold (0-1)"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Identify users at risk based on low progress."""
    async def _run():
        async with AsyncMoodleClient() as client:
            progress_service = ProgressService(client)
            from services.enrollment_service import EnrollmentService
            enrollment_service = EnrollmentService(client)

            try:
                # Get enrolled users
                users = await enrollment_service.list_enrolled_users(course_id)
                user_ids = [u.id for u in users]

                # Get completions
                completions = await progress_service.bulk_get_completions(user_ids, course_id)

                # Identify at-risk users
                at_risk_ids = get_at_risk_users(
                    [await progress_service.get_user_progress(uid) for uid in user_ids],
                    threshold=threshold,
                )

                if format == "json":
                    console.print_json(data=json.dumps(at_risk_ids))
                else:
                    console.print(f"[bold red]At-Risk Users - Course {course_id}[/]")
                    console.print(f"Threshold: {threshold * 100}% completion\n")

                    if not at_risk_ids:
                        console.print("[green]No at-risk users found![/]")
                        return

                    table = Table(title=f"At-Risk Users ({len(at_risk_ids)} found)")
                    table.add_column("User ID", style="cyan")
                    table.add_column("User")
                    table.add_column("Completion %", justify="right")

                    for user_id in at_risk_ids[:20]:  # Limit to 20 for display
                        user = next((u for u in users if u.id == user_id), None)
                        completion = next((c for c in completions if c.user_id == user_id), None)

                        if user and completion:
                            table.add_row(
                                str(user_id),
                                user.fullname,
                                f"{completion.completion_percentage:.1f}%",
                            )

                    console.print(table)

                    if len(at_risk_ids) > 20:
                        console.print(f"\n[dim]... and {len(at_risk_ids) - 20} more[/]")

            except Exception as e:
                print_error(f"Failed to identify at-risk users: {e}")

    asyncio.run(_run())