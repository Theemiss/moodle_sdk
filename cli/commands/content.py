"""Content management CLI commands."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns

from client.moodle_client import AsyncMoodleClient
from services.content_service import ContentService
from schemas.content import ActivityType
from cli.output import print_error, print_success

app = typer.Typer(help="Course content and activity commands")
console = Console()


@app.command("list")
def list_activities(
    course_id: int = typer.Argument(..., help="Course ID"),
    activity_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by activity type"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List all activities in a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                if activity_type:
                    activities = await service.get_activities_by_type(course_id, activity_type)
                else:
                    activities = await service.get_course_activities(course_id)
                
                if format == "json":
                    data = [a.model_dump() for a in activities]
                    console.print_json(data=json.dumps(data))
                else:
                    console.print(f"[bold]Course {course_id} - Activities[/]")
                    console.print(f"Total: {len(activities)}\n")
                    
                    # Group by section for better display
                    from collections import defaultdict
                    by_section = defaultdict(list)
                    for act in activities:
                        by_section[act.section_number].append(act)
                    
                    for section_num in sorted(by_section.keys()):
                        section_acts = by_section[section_num]
                        section_name = section_acts[0].section_name if section_acts else f"Section {section_num}"
                        
                        panel = Panel(
                            "\n".join([
                                f"[cyan]{act.modname}[/] {act.name} [dim](ID: {act.id})[/]" 
                                for act in section_acts
                            ]),
                            title=f"[bold]Section {section_num}: {section_name}[/]",
                            border_style="blue",
                        )
                        console.print(panel)
                        
            except Exception as e:
                print_error(f"Failed to list activities: {e}")
    
    asyncio.run(_run())


@app.command("get")
def get_activity(
    cmid: int = typer.Argument(..., help="Course module ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get detailed information about a specific activity."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                activity = await service.get_activity_detail(cmid)
                
                if format == "json":
                    console.print_json(data=json.dumps(activity.model_dump()))
                else:
                    # Basic info
                    console.print(Panel(
                        f"[bold]Activity:[/] {activity.name}\n"
                        f"[bold]Type:[/] {activity.modname}\n"
                        f"[bold]Course:[/] {activity.course_id}\n"
                        f"[bold]Section:[/] {activity.section_number}: {activity.section_name}\n"
                        f"[bold]Visible:[/] {'Yes' if activity.visible else 'No'}\n"
                        f"[bold]Completion:[/] {'Enabled' if activity.completion else 'Disabled'}",
                        title=f"Activity {cmid}",
                        border_style="green",
                    ))
                    
                    # Description if available
                    if activity.description:
                        console.print(Panel(
                            activity.description[:500] + "..." if len(activity.description) > 500 else activity.description,
                            title="Description",
                            border_style="dim",
                        ))
                    
                    # Type-specific details
                    type_details = None
                    if activity.assignment_details:
                        type_details = activity.assignment_details
                    elif activity.quiz_details:
                        type_details = activity.quiz_details
                    elif activity.scorm_details:
                        type_details = activity.scorm_details
                    elif activity.h5p_details:
                        type_details = activity.h5p_details
                    
                    if type_details:
                        details_table = Table(title=f"{activity.modname.title()} Details")
                        details_table.add_column("Property", style="cyan")
                        details_table.add_column("Value")
                        
                        for key, value in type_details.model_dump().items():
                            if value is not None:
                                details_table.add_row(key.replace('_', ' ').title(), str(value))
                        
                        console.print(details_table)
                    
                    # Contents if any
                    if activity.contents:
                        contents_table = Table(title="Contents")
                        contents_table.add_column("File", style="green")
                        contents_table.add_column("Size", justify="right")
                        contents_table.add_column("Type")
                        
                        for content in activity.contents[:5]:  # Show first 5
                            size = f"{content.filesize / 1024:.1f} KB" if content.filesize else "-"
                            contents_table.add_row(
                                content.filename,
                                size,
                                content.type,
                            )
                        
                        console.print(contents_table)
                        if len(activity.contents) > 5:
                            console.print(f"[dim]... and {len(activity.contents) - 5} more files[/]")
                    
            except Exception as e:
                print_error(f"Failed to get activity: {e}")
    
    asyncio.run(_run())


@app.command("summary")
def content_summary(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get a summary of all content in a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                summary = await service.get_course_content_summary(course_id)
                
                if format == "json":
                    console.print_json(data=json.dumps(summary.model_dump()))
                else:
                    console.print(f"[bold]Course {course_id} - Content Summary[/]")
                    console.print(f"Total Activities: {summary.total_activities}")
                    console.print(f"Total Sections: {summary.total_sections}")
                    console.print(f"Completion Tracking: {'Enabled' if summary.completion_tracking_enabled else 'Disabled'}\n")
                    
                    # Activity types breakdown
                    if summary.activity_types:
                        type_table = Table(title="Activity Types")
                        type_table.add_column("Type", style="cyan")
                        type_table.add_column("Count", justify="right")
                        
                        for act_type, count in sorted(summary.activity_types.items()):
                            type_table.add_row(act_type, str(count))
                        
                        console.print(type_table)
                    
            except Exception as e:
                print_error(f"Failed to get content summary: {e}")
    
    asyncio.run(_run())


@app.command("completion")
def activity_completion(
    course_id: int = typer.Argument(..., help="Course ID"),
    user_id: int = typer.Argument(..., help="User ID"),
    cmid: Optional[int] = typer.Option(None, "--cmid", help="Specific activity CMID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get activity completion status for a user."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                completions = await service.get_user_activity_completion(course_id, user_id, cmid)
                
                if format == "json":
                    data = [c.model_dump() for c in completions]
                    console.print_json(data=json.dumps(data))
                else:
                    if cmid:
                        console.print(f"[bold]Activity Completion for User {user_id}[/]")
                    else:
                        console.print(f"[bold]All Activities Completion for User {user_id} in Course {course_id}[/]")
                    
                    table = Table()
                    table.add_column("CMID", style="cyan")
                    table.add_column("Activity")
                    table.add_column("Status")
                    table.add_column("Completed", justify="center")
                    table.add_column("Grade", justify="right")
                    
                    # Get activity names for context
                    content_service = ContentService(client)
                    activities = {a.id: a for a in await content_service.get_course_activities(course_id)}
                    
                    for comp in completions:
                        activity = activities.get(comp.cmid)
                        name = activity.name if activity else f"Activity {comp.cmid}"
                        
                        status_map = {
                            0: "⏳ Incomplete",
                            1: "✅ Complete",
                            2: "⭐ Complete (Pass)",
                            3: "❌ Complete (Fail)",
                        }
                        status = status_map.get(comp.state, "Unknown")
                        
                        completed = "-"
                        if comp.timecompleted:
                            from datetime import datetime
                            completed = datetime.fromtimestamp(comp.timecompleted).strftime("%Y-%m-%d")
                        
                        grade = f"{comp.grade:.1f}" if comp.grade is not None else "-"
                        
                        table.add_row(
                            str(comp.cmid),
                            name[:30] + "..." if len(name) > 30 else name,
                            status,
                            completed,
                            grade,
                        )
                    
                    console.print(table)
                    
            except Exception as e:
                print_error(f"Failed to get completion status: {e}")
    
    asyncio.run(_run())


@app.command("grades")
def activity_grades(
    course_id: int = typer.Argument(..., help="Course ID"),
    activity_id: int = typer.Argument(..., help="Activity instance ID"),
    activity_type: str = typer.Option(..., "--type", "-t", help="Activity type"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get grades for a specific activity."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                grades = await service.get_activity_grades(course_id, activity_id, activity_type)
                
                if format == "json":
                    console.print_json(data=json.dumps(grades.model_dump()))
                else:
                    console.print(f"[bold]Grades for {activity_type} {activity_id}[/]")
                    
                    if grades.maxgrade:
                        console.print(f"Max Grade: {grades.maxgrade}")
                    if grades.gradepass:
                        console.print(f"Pass Grade: {grades.gradepass}")
                    console.print("")
                    
                    if grades.grades:
                        table = Table()
                        table.add_column("User ID", style="cyan")
                        table.add_column("Grade", justify="right")
                        table.add_column("Percentage", justify="right")
                        table.add_column("Status")
                        
                        for g in grades.grades:
                            table.add_row(
                                str(g.get("userid", "")),
                                str(g.get("grade", "-")),
                                f"{g.get('percentage', 0):.1f}%" if g.get("percentage") else "-",
                                g.get("status", "unknown"),
                            )
                        
                        console.print(table)
                    else:
                        console.print("[yellow]No grades found[/]")
                    
            except Exception as e:
                print_error(f"Failed to get activity grades: {e}")
    
    asyncio.run(_run())


@app.command("toggle")
def toggle_visibility(
    cmid: int = typer.Argument(..., help="Course module ID"),
    hide: bool = typer.Option(False, "--hide", help="Hide the activity"),
    show: bool = typer.Option(False, "--show", help="Show the activity"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Toggle activity visibility."""
    if hide == show:
        print_error("Must specify either --hide or --show")
        return
    
    visible = show
    
    async def _run():
        if dry_run:
            action = "show" if visible else "hide"
            console.print(f"[yellow]DRY RUN: Would {action} activity {cmid}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                await service.toggle_activity_visibility(cmid, visible)
                action = "shown" if visible else "hidden"
                print_success(f"Activity {cmid} {action}")
            except Exception as e:
                print_error(f"Failed to toggle visibility: {e}")
    
    asyncio.run(_run())


@app.command("attempts")
def activity_attempts(
    activity_id: int = typer.Argument(..., help="Activity instance ID"),
    activity_type: str = typer.Option(..., "--type", "-t", help="Activity type"),
    user_id: Optional[int] = typer.Option(None, "--user", "-u", help="User ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get user attempts for an activity."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = ContentService(client)
            
            try:
                attempts = await service.get_activity_attempts(activity_id, activity_type, user_id)
                
                if format == "json":
                    data = [a.model_dump() for a in attempts]
                    console.print_json(data=json.dumps(data))
                else:
                    if not attempts:
                        console.print("[yellow]No attempts found[/]")
                        return
                    
                    table = Table(title=f"Attempts for {activity_type} {activity_id}")
                    table.add_column("Attempt", justify="right", style="cyan")
                    table.add_column("User", justify="right")
                    table.add_column("Start")
                    table.add_column("Finish")
                    table.add_column("Score", justify="right")
                    table.add_column("Status")
                    
                    for att in attempts:
                        start = "-"
                        if att.time_start:
                            from datetime import datetime
                            start = datetime.fromtimestamp(att.time_start).strftime("%Y-%m-%d %H:%M")
                        
                        finish = "-"
                        if att.time_finish:
                            from datetime import datetime
                            finish = datetime.fromtimestamp(att.time_finish).strftime("%Y-%m-%d %H:%M")
                        
                        score = f"{att.score:.1f}/{att.maxscore:.1f}" if att.score and att.maxscore else str(att.score) if att.score else "-"
                        
                        table.add_row(
                            str(att.attempt_number),
                            str(att.user_id),
                            start,
                            finish,
                            score,
                            att.status,
                        )
                    
                    console.print(table)
                    
            except Exception as e:
                print_error(f"Failed to get attempts: {e}")
    
    asyncio.run(_run())