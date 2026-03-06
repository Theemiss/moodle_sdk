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
)
from cli.output import print_error

app = typer.Typer(help="Progress tracking commands")
console = Console()


def _to_json(model) -> str:
    """
    BUG 5 FIX: Serialize Pydantic model to JSON safely.

    The original code called json.dumps(model.model_dump()) throughout this file.
    model_dump() returns Python-native types — datetime objects for timecompleted
    fields — which json.dumps() cannot serialize:
        TypeError: Object of type datetime is not JSON serializable

    Fix: model_dump(mode='json') converts all types to JSON-safe equivalents
    (datetimes → ISO strings, etc.) before passing to json.dumps().
    """
    return json.dumps(model.model_dump(mode="json"), indent=2)


def _list_to_json(models) -> str:
    return json.dumps([m.model_dump(mode="json") for m in models], indent=2)


@app.command("report")
def progress_report(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: Optional[int] = typer.Option(None, "--course-id", "-c", help="Filter to a specific course"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Get progress report for a user."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = ProgressService(client)
            try:
                if course_id:
                    completion = await service.get_course_completion(user_id, course_id)

                    if output_format == "json":
                        console.print_json(_to_json(completion))   # BUG 5 FIX
                        return

                    console.print(f"\n[bold]Progress: User {user_id} in Course {course_id}[/]\n")

                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                    ) as bar:
                        bar.add_task(
                            "Completion",
                            total=max(completion.total_activities, 1),
                            completed=completion.activities_completed,
                        )

                    status_str = "[green]Completed[/]" if completion.completed else "[yellow]In Progress[/]"
                    console.print(f"Status:     {status_str}")
                    console.print(f"Activities: {completion.activities_completed}/{completion.total_activities}")
                    if completion.timecompleted:
                        console.print(f"Completed:  {completion.timecompleted.strftime('%Y-%m-%d %H:%M')}")

                    if completion.activities:
                        table = Table(title="Activity Breakdown")
                        table.add_column("Activity")
                        table.add_column("Type", style="dim")
                        table.add_column("Status", justify="center")
                        table.add_column("Date", justify="center")

                        state_labels = {
                            0: "⏳ Incomplete",
                            1: "✅ Complete",
                            2: "⭐ Pass",
                            3: "❌ Fail",
                        }
                        for act in completion.activities:
                            table.add_row(
                                act.activity_name,
                                act.activity_type,
                                state_labels.get(act.state, "?"),
                                act.timecompleted.strftime("%Y-%m-%d") if act.timecompleted else "—",
                            )
                        console.print(table)

                else:
                    progress = await service.get_user_progress(user_id)

                    if output_format == "json":
                        console.print_json(_to_json(progress))   # BUG 5 FIX
                        return

                    console.print(f"\n[bold]Overall Progress: User {user_id}[/]\n")
                    console.print(f"Enrolled courses:   {len(progress.enrolled_courses)}")
                    console.print(f"Completed:          {progress.completed_courses}")
                    console.print(f"In progress:        {progress.in_progress_courses}")
                    console.print(f"Overall completion: {progress.overall_completion_percentage:.1f}%\n")

                    if progress.course_completions:
                        table = Table(title="Course Breakdown")
                        table.add_column("Course ID", style="cyan")
                        table.add_column("Completion %", justify="right")
                        table.add_column("Activities", justify="center")
                        table.add_column("Status")

                        for cid, comp in progress.course_completions.items():
                            status_str = "[green]Completed[/]" if comp.completed else "[yellow]In Progress[/]"
                            table.add_row(
                                str(cid),
                                f"{comp.completion_percentage:.1f}%",
                                f"{comp.activities_completed}/{comp.total_activities}",
                                status_str,
                            )
                        console.print(table)

            except Exception as exc:
                print_error(f"Failed to get progress report: {exc}")

    asyncio.run(_run())


@app.command("completion")
def course_completion(
    course_id: int = typer.Argument(..., help="Course ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Show completion statistics for all enrolled users in a course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            progress_service = ProgressService(client)
            from services.enrollment_service import EnrollmentService
            enrollment_service = EnrollmentService(client)

            try:
                users = await enrollment_service.list_enrolled_users(course_id)
                user_ids = [u.id for u in users]

                completions = await progress_service.bulk_get_completions(user_ids, course_id)

                if output_format == "json":
                    console.print_json(_list_to_json(completions))   # BUG 5 FIX
                    return

                completion_rate = compute_completion_rate(completions)
                console.print(f"\n[bold]Course Completion — Course {course_id}[/]\n")
                console.print(f"Enrolled:        {len(user_ids)}")
                console.print(f"Completion rate: {completion_rate * 100:.1f}%\n")

                table = Table(title="User Completion")
                table.add_column("User ID", style="cyan", no_wrap=True)
                table.add_column("Name")
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

            except Exception as exc:
                print_error(f"Failed to get completion data: {exc}")

    asyncio.run(_run())


@app.command("at-risk")
def at_risk_users(
    course_id: int = typer.Argument(..., help="Course ID"),
    threshold: float = typer.Option(0.3, "--threshold", "-t", help="Risk threshold (0.0–1.0)"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Identify users at risk based on low completion progress."""

    async def _run():
        async with AsyncMoodleClient() as client:
            progress_service = ProgressService(client)
            from services.enrollment_service import EnrollmentService
            enrollment_service = EnrollmentService(client)

            try:
                users = await enrollment_service.list_enrolled_users(course_id)
                user_ids = [u.id for u in users]

                # BUG 6 FIX: The original code:
                #   1. Called bulk_get_completions(user_ids, course_id) — stored in `completions`
                #   2. Then called [await get_user_progress(uid) for uid in user_ids] — N more calls
                #   3. Passed the UserProgress list to get_at_risk_users
                #   4. Never used `completions` at all — it was fetched and thrown away
                #
                # get_at_risk_users takes List[UserProgress] and checks overall_completion_percentage.
                # But for a single-course at-risk check, we already have everything we need from
                # bulk_get_completions. Pass completions directly to a simpler threshold check,
                # saving N additional get_user_progress calls (each of which fetches ALL courses
                # the user is enrolled in — extremely wasteful for a single-course operation).
                completions = await progress_service.bulk_get_completions(user_ids, course_id)

                # Identify at-risk by completion_percentage directly from the course data
                at_risk = [
                    c for c in completions
                    if (c.completion_percentage / 100.0) < threshold
                ]

                if output_format == "json":
                    console.print_json(_list_to_json(at_risk))   # BUG 5 FIX
                    return

                console.print(f"\n[bold red]At-Risk Users — Course {course_id}[/]")
                console.print(f"Threshold: below {threshold * 100:.0f}% completion\n")

                if not at_risk:
                    console.print("[green]✓ No at-risk users found.[/]")
                    return

                table = Table(title=f"At-Risk Users ({len(at_risk)} of {len(user_ids)})")
                table.add_column("User ID", style="cyan", no_wrap=True)
                table.add_column("Name")
                table.add_column("Completion %", justify="right")
                table.add_column("Activities", justify="center")

                # Sort by completion % ascending (worst first)
                at_risk.sort(key=lambda c: c.completion_percentage)

                for completion in at_risk[:50]:  # cap at 50 rows
                    user = next((u for u in users if u.id == completion.user_id), None)
                    table.add_row(
                        str(completion.user_id),
                        user.fullname if user else "—",
                        f"[red]{completion.completion_percentage:.1f}%[/]",
                        f"{completion.activities_completed}/{completion.total_activities}",
                    )

                console.print(table)

                if len(at_risk) > 50:
                    console.print(f"\n[dim]... and {len(at_risk) - 50} more[/]")

            except Exception as exc:
                print_error(f"Failed to identify at-risk users: {exc}")

    asyncio.run(_run())