"""Activity log CLI commands."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from analytics.engagement_analytics import EngagementAnalytics
from cli.output import print_error
from client.moodle_client import AsyncMoodleClient
from services.activity_service import ActivityService

app = typer.Typer(help="Activity log commands")
console = Console()


def _to_json(models) -> str:
    """
    BUG 8 FIX: Serialize a list of ActivityLog models to JSON safely.

    model_dump() without mode='json' returns datetime objects which json.dumps()
    cannot serialize. mode='json' converts datetimes to ISO strings.
    """
    return json.dumps([m.model_dump(mode="json") for m in models], indent=2)


def _fmt_time(dt: Optional[datetime]) -> str:
    """
    BUG 4 FIX: Safe datetime formatting.

    The original code called log.timecreated.strftime(...) directly.
    ActivityLog.timecreated is Optional[datetime] — when Moodle returns a
    timestamp of 0 or omits the field, timecreated is None and strftime raises:
        AttributeError: 'NoneType' object has no attribute 'strftime'
    """
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M")


def _parse_since(since_str: Optional[str], default_days: int = 7) -> datetime:
    """Parse a YYYY-MM-DD string or return a default lookback datetime."""
    if since_str:
        return datetime.strptime(since_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc) - timedelta(days=default_days)


@app.command("course")
def course_logs(
    course_id: int = typer.Argument(..., help="Course ID"),
    since: Optional[str] = typer.Option(None, "--since", help="Show logs since date (YYYY-MM-DD)"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max number of logs to display"),
) -> None:
    """Show activity logs for a course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = ActivityService(client)
            try:
                since_date = _parse_since(since, default_days=7)
                logs = await service.get_course_logs(course_id, since_date, limit)

                if output_format == "json":
                    console.print_json(_to_json(logs))   # BUG 8 FIX
                    return

                if not logs:
                    console.print(
                        f"[yellow]No logs for course {course_id} since {since_date.date()}[/]"
                    )
                    return

                unique_users = len({l.user_id for l in logs})
                event_types = len({l.event_name for l in logs})

                console.print(
                    Panel(
                        f"[bold]Course Activity — Course {course_id}[/]\n"
                        f"Period:       {since_date.date()} → {datetime.now().date()}\n"
                        f"Total events: {len(logs)}\n"
                        f"Unique users: {unique_users}\n"
                        f"Event types:  {event_types}",
                        border_style="blue",
                    )
                )

                table = Table()
                table.add_column("Time", style="cyan", no_wrap=True)
                table.add_column("User ID", justify="right")
                table.add_column("Event")
                table.add_column("Component")
                table.add_column("Object", style="dim")

                for log in logs[:limit]:
                    table.add_row(
                        _fmt_time(log.timecreated),   # BUG 4 FIX
                        str(log.user_id),
                        log.event_name,
                        log.component,
                        f"{log.object_table}:{log.object_id}" if log.object_table else "—",
                    )

                console.print(table)

                if len(logs) == limit:
                    console.print(f"\n[dim]Showing {limit} logs — use --limit to see more[/]")

            except Exception as exc:
                print_error(f"Failed to get course logs: {exc}")

    asyncio.run(_run())


@app.command("user")
def user_logs(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: Optional[int] = typer.Option(None, "--course-id", "-c", help="Filter by course"),
    since: Optional[str] = typer.Option(None, "--since", help="Show logs since (YYYY-MM-DD)"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Show activity logs for a user."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = ActivityService(client)
            try:
                since_date = _parse_since(since, default_days=30)
                logs = await service.get_user_logs(user_id, course_id, since_date)

                if output_format == "json":
                    console.print_json(_to_json(logs))   # BUG 8 FIX
                    return

                if not logs:
                    console.print(
                        f"[yellow]No logs for user {user_id} since {since_date.date()}[/]"
                    )
                    return

                analytics = EngagementAnalytics(logs)
                score = analytics.compute_user_engagement_score(user_id)

                console.print(
                    Panel(
                        f"[bold]User Activity — User {user_id}[/]\n"
                        f"Period:           {since_date.date()} → {datetime.now().date()}\n"
                        f"Total events:     {len(logs)}\n"
                        f"Engagement score: {score:.1f}/100",
                        border_style="blue",
                    )
                )

                # Activity breakdown by course
                from collections import defaultdict
                course_counts: dict = defaultdict(int)
                for log in logs:
                    if log.course_id:
                        course_counts[log.course_id] += 1

                if course_counts:
                    console.print("\n[bold]Activity by course:[/]")
                    for cid, count in sorted(course_counts.items(), key=lambda x: x[1], reverse=True):
                        console.print(f"  Course {cid}: {count} events")

                console.print("\n[bold]Recent activity:[/]")
                for log in logs[:20]:
                    console.print(
                        f"  [dim]{_fmt_time(log.timecreated)}[/]  "   # BUG 4 FIX
                        f"{log.event_name}  [dim]{log.component}[/]"
                    )

            except Exception as exc:
                print_error(f"Failed to get user logs: {exc}")

    asyncio.run(_run())


@app.command("hotspots")
def activity_hotspots(
    course_id: int = typer.Argument(..., help="Course ID"),
    since: Optional[str] = typer.Option(None, "--since", help="Analyze since date (YYYY-MM-DD)"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Identify the most active areas in a course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = ActivityService(client)
            try:
                since_date = _parse_since(since, default_days=30)
                logs = await service.get_course_logs(course_id, since_date, limit=10_000)
                analytics = EngagementAnalytics(logs)
                hotspots = analytics.get_activity_hotspots(course_id)

                if output_format == "json":
                    # hotspots is a list of dicts — serialize datetimes manually
                    serializable = [
                        {
                            **h,
                            "last_access": h["last_access"].isoformat() if isinstance(h.get("last_access"), datetime) else h.get("last_access"),
                        }
                        for h in hotspots
                    ]
                    console.print_json(json.dumps(serializable))
                    return

                console.print(f"[bold]Activity Hotspots — Course {course_id}[/]")
                console.print(f"Period: {since_date.date()} → {datetime.now().date()}\n")

                table = Table()
                table.add_column("Activity ID", style="cyan")
                table.add_column("Access Count", justify="right")
                table.add_column("Engagement %", justify="right")
                table.add_column("Last Access", no_wrap=True)

                for hotspot in hotspots:
                    last = hotspot.get("last_access")
                    table.add_row(
                        str(hotspot["activity_id"]),
                        str(hotspot["access_count"]),
                        f"{hotspot['engagement_score']:.1f}%",
                        _fmt_time(last) if isinstance(last, datetime) else str(last or "—"),
                    )

                console.print(table)

            except Exception as exc:
                print_error(f"Failed to analyze hotspots: {exc}")

    asyncio.run(_run())