"""Activity log CLI commands."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from client.moodle_client import AsyncMoodleClient
from services.activity_service import ActivityService
from analytics.engagement_analytics import EngagementAnalytics
from cli.output import print_error

app = typer.Typer(help="Activity log commands")
console = Console()


@app.command("course")
def course_logs(
    course_id: int = typer.Argument(..., help="Course ID"),
    since: Optional[str] = typer.Option(None, "--since", help="Show logs since date (YYYY-MM-DD)"),
    format: str = typer.Option("table", "--format", help="Output format"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max number of logs"),
) -> None:
    """Show activity logs for a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ActivityService(client)

            try:
                # Parse since date
                since_date = None
                if since:
                    since_date = datetime.strptime(since, "%Y-%m-%d")
                else:
                    since_date = datetime.now() - timedelta(days=7)  # Default to last 7 days

                logs = await service.get_course_logs(course_id, since_date, limit)

                if format == "json":
                    data = [l.model_dump() for l in logs]
                    console.print_json(data=json.dumps(data))
                else:
                    if not logs:
                        console.print(f"[yellow]No logs found for course {course_id} since {since_date.date()}[/]")
                        return

                    # Summary stats
                    unique_users = len(set(l.user_id for l in logs))
                    event_types = len(set(l.event_name for l in logs))

                    console.print(Panel(
                        f"[bold]Course Activity - Course {course_id}[/]\n"
                        f"Period: {since_date.date()} to {datetime.now().date()}\n"
                        f"Total Events: {len(logs)}\n"
                        f"Unique Users: {unique_users}\n"
                        f"Event Types: {event_types}",
                        border_style="blue",
                    ))

                    # Log table
                    table = Table()
                    table.add_column("Time", style="cyan")
                    table.add_column("User ID", justify="right")
                    table.add_column("Event")
                    table.add_column("Component")
                    table.add_column("Object", style="dim")

                    for log in logs[:limit]:
                        table.add_row(
                            log.timecreated.strftime("%Y-%m-%d %H:%M"),
                            str(log.user_id),
                            log.event_name,
                            log.component,
                            f"{log.object_table}:{log.object_id}" if log.object_table else "-",
                        )

                    console.print(table)

                    if len(logs) > limit:
                        console.print(f"\n[dim]Showing first {limit} of {len(logs)} logs[/]")

            except Exception as e:
                print_error(f"Failed to get course logs: {e}")


@app.command("user")
def user_logs(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: Optional[int] = typer.Option(None, "--course-id", "-c", help="Filter by course"),
    since: Optional[str] = typer.Option(None, "--since", help="Show logs since date (YYYY-MM-DD)"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Show activity logs for a user."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ActivityService(client)

            try:
                since_date = None
                if since:
                    since_date = datetime.strptime(since, "%Y-%m-%d")
                else:
                    since_date = datetime.now() - timedelta(days=30)

                logs = await service.get_user_logs(user_id, course_id, since_date)

                if format == "json":
                    data = [l.model_dump() for l in logs]
                    console.print_json(data=json.dumps(data))
                else:
                    if not logs:
                        console.print(f"[yellow]No logs found for user {user_id} since {since_date.date()}[/]")
                        return

                    # Engagement score
                    analytics = EngagementAnalytics(logs)
                    score = analytics.compute_user_engagement_score(user_id)

                    console.print(Panel(
                        f"[bold]User Activity - User {user_id}[/]\n"
                        f"Period: {since_date.date()} to {datetime.now().date()}\n"
                        f"Total Events: {len(logs)}\n"
                        f"Engagement Score: {score:.1f}/100",
                        border_style="blue",
                    ))

                    # Group by course
                    from collections import defaultdict
                    course_counts = defaultdict(int)
                    for log in logs:
                        if log.course_id:
                            course_counts[log.course_id] += 1

                    if course_counts:
                        console.print("\n[bold]Activity by Course:[/]")
                        for cid, count in sorted(course_counts.items(), key=lambda x: x[1], reverse=True):
                            console.print(f"  Course {cid}: {count} events")

                    # Recent logs
                    console.print("\n[bold]Recent Activity:[/]")
                    for log in logs[:20]:
                        console.print(
                            f"  [dim]{log.timecreated.strftime('%Y-%m-%d %H:%M')}[/] "
                            f"{log.event_name} in {log.component}"
                        )

            except Exception as e:
                print_error(f"Failed to get user logs: {e}")


@app.command("hotspots")
def activity_hotspots(
    course_id: int = typer.Argument(..., help="Course ID"),
    since: Optional[str] = typer.Option(None, "--since", help="Analyze since date"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Identify most active areas in a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ActivityService(client)

            try:
                since_date = None
                if since:
                    since_date = datetime.strptime(since, "%Y-%m-%d")
                else:
                    since_date = datetime.now() - timedelta(days=30)

                logs = await service.get_course_logs(course_id, since_date, limit=10000)
                analytics = EngagementAnalytics(logs)
                hotspots = analytics.get_activity_hotspots(course_id)

                if format == "json":
                    console.print_json(data=json.dumps(hotspots))
                else:
                    console.print(f"[bold]Activity Hotspots - Course {course_id}[/]")
                    console.print(f"Period: {since_date.date()} to {datetime.now().date()}\n")

                    table = Table()
                    table.add_column("Activity ID", style="cyan")
                    table.add_column("Access Count", justify="right")
                    table.add_column("Engagement Score", justify="right")
                    table.add_column("Last Access")

                    for hotspot in hotspots:
                        table.add_row(
                            str(hotspot["activity_id"]),
                            str(hotspot["access_count"]),
                            f"{hotspot['engagement_score']:.1f}%",
                            hotspot["last_access"].strftime("%Y-%m-%d %H:%M") if hotspot["last_access"] else "-",
                        )

                    console.print(table)

            except Exception as e:
                print_error(f"Failed to analyze hotspots: {e}")