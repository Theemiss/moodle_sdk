"""Admin management CLI commands with only real Moodle APIs."""

import asyncio
import json
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from client.moodle_client import AsyncMoodleClient
from services.admin_service import AdminService
from cli.output import print_error, print_success, print_warning

app = typer.Typer(help="System administration commands")
console = Console()


@app.command("health")
def health_check(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed health info"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Check Moodle system health using available APIs."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = AdminService(client)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Checking system health...", total=None)
                health = await service.check_system_health()
            
            if format == "json":
                # Handle datetime serialization
                def json_serializer(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")
    
                console.print_json(data=json.dumps(health.model_dump(), default=json_serializer))
            else:
                # Overall status
                status_color = "green" if health.overall_status == "healthy" else "red" if health.overall_status == "down" else "yellow"
                console.print(Panel(
                    f"[bold]Overall Status:[/] [{status_color}]{health.overall_status.upper()}[/]\n"
                    f"[bold]Last Check:[/] {health.last_check.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"[bold]Response Time:[/] {health.response_time}ms",
                    title="System Health",
                    border_style=status_color,
                ))
                
                # Component status
                table = Table(title="Component Health", box=box.ROUNDED)
                table.add_column("Component", style="cyan")
                table.add_column("Status", justify="center")
                table.add_column("Details")
                table.add_column("Latency", justify="right")
                
                for comp in health.components:
                    status_icon = "✅" if comp.status == "healthy" else "❌" if comp.status == "down" else "⚠️"
                    status_color = "green" if comp.status == "healthy" else "red" if comp.status == "down" else "yellow"
                    table.add_row(
                        comp.name,
                        f"[{status_color}]{status_icon} {comp.status}[/]",
                        comp.details or "-",
                        f"{comp.latency}ms" if comp.latency else "-",
                    )
                
                console.print(table)
                
                if verbose and health.warnings:
                    console.print("\n[yellow]Warnings:[/]")
                    for warning in health.warnings:
                        console.print(f"  ⚠️  {warning}")
    
    asyncio.run(_run())


@app.command("status")
def system_status(
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Display system status information from available APIs."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = AdminService(client)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Fetching system status...", total=None)
                status = await service.get_system_status()
            
            if format == "json":
                console.print_json(data=json.dumps(status.model_dump()))
            else:
                # Basic Info
                console.print(Panel(
                    f"[bold]Moodle Version:[/] {status.version}\n"
                    f"[bold]Release:[/] {status.release}\n"
                    f"[bold]Site URL:[/] {status.site_url}\n"
                    f"[bold]Site Name:[/] {status.site_name}\n"
                    f"[bold]Last Cron:[/] {status.last_cron.strftime('%Y-%m-%d %H:%M') if status.last_cron else 'Never'}",
                    title="System Information",
                    border_style="blue",
                ))
                
                # Statistics
                stats_table = Table(title="Site Statistics", box=box.ROUNDED)
                stats_table.add_column("Metric", style="cyan")
                stats_table.add_column("Count", justify="right")
                
                stats_table.add_row("Total Users", f"{status.total_users:,}")
                stats_table.add_row("Active Users (30d)", f"{status.active_users:,}")
                stats_table.add_row("Total Courses", f"{status.total_courses:,}")
                stats_table.add_row("Active Courses", f"{status.active_courses:,}")
                stats_table.add_row("Total Categories", f"{status.total_categories:,}")
                
                console.print(stats_table)
                
                console.print("\n[dim]Note: Disk usage and database size are not available via Moodle APIs[/]")
    
    asyncio.run(_run())


@app.command("tasks")
def list_tasks(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending, running, completed, failed, disabled)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of tasks to show"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List scheduled tasks (core_cron_get_scheduled_tasks)."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = AdminService(client)
            tasks = await service.get_scheduled_tasks(status=status, limit=limit)
            
            if format == "json":
                data = [t.model_dump() for t in tasks]
                console.print_json(data=json.dumps(data))
            else:
                if not tasks:
                    console.print("[yellow]No tasks found[/]")
                    return
                    
                table = Table(title="Scheduled Tasks", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Name")
                table.add_column("Type")
                table.add_column("Schedule")
                table.add_column("Last Run")
                table.add_column("Next Run")
                table.add_column("Status", justify="center")
                
                status_colors = {
                    "pending": "yellow",
                    "running": "blue",
                    "completed": "green",
                    "failed": "red",
                    "disabled": "dim",
                }
                
                for task in tasks:
                    status_display = f"[{status_colors.get(task.status, 'white')}]{task.status.upper()}[/]"
                    
                    table.add_row(
                        str(task.id),
                        task.name,
                        task.type,
                        task.schedule or "-",
                        task.last_run.strftime("%Y-%m-%d %H:%M") if task.last_run else "-",
                        task.next_run.strftime("%Y-%m-%d %H:%M") if task.next_run else "-",
                        status_display,
                    )
                
                console.print(table)
    
    asyncio.run(_run())


@app.command("run-task")
def run_task(
    task_id: int = typer.Argument(..., help="Task ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be run without executing"),
) -> None:
    """Run a specific scheduled task (core_cron_run_scheduled_task)."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would run task ID {task_id}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = AdminService(client)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(description=f"Running task {task_id}...", total=None)
                
                result = await service.run_scheduled_task(task_id)
                
                progress.update(task, completed=True)
            
            if result.success:
                print_success(f"Task {task_id} completed in {result.duration}ms")
                if result.output:
                    console.print(result.output)
            else:
                print_error(f"Task {task_id} failed: {result.error}")
    
    asyncio.run(_run())


@app.command("recent-activity")
def recent_activity(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look back"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Show recent course activity (based on course modification times)."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = AdminService(client)
            activities = await service.get_recent_course_activity(days=days)
            
            if format == "json":
                console.print_json(data=json.dumps(activities))
            else:
                if not activities:
                    console.print(f"[yellow]No course activity in the last {days} days[/]")
                    return
                    
                table = Table(title=f"Course Activity (Last {days} Days)", box=box.ROUNDED)
                table.add_column("Course ID", style="cyan")
                table.add_column("Course Name")
                table.add_column("Last Modified")
                table.add_column("Activity")
                
                for act in activities:
                    table.add_row(
                        str(act["id"]),
                        act["fullname"],
                        act["timemodified"].strftime("%Y-%m-%d %H:%M"),
                        act["activity"],
                    )
                
                console.print(table)
    
    asyncio.run(_run())


@app.command("completion-stats")
def completion_stats(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get course completion statistics."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = AdminService(client)
            stats = await service.get_course_completion_stats(course_id)
            
            if format == "json":
                console.print_json(data=json.dumps(stats))
            else:
                if "error" in stats:
                    print_error(f"Failed to get stats: {stats['error']}")
                    return
                    
                console.print(Panel(
                    f"[bold]Course ID:[/] {stats['course_id']}\n"
                    f"[bold]Total Users:[/] {stats['total_users']}\n"
                    f"[bold]Completed:[/] {stats['completed_users']}\n"
                    f"[bold]Completion Rate:[/] {stats['completion_rate']:.1f}%",
                    title="Course Completion Statistics",
                    border_style="green",
                ))
    
    asyncio.run(_run())