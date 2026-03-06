"""Course management CLI commands."""

import asyncio
import json
from datetime import datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from client.moodle_client import AsyncMoodleClient
from schemas.course import CourseCreate, CourseUpdate
from schemas.reset import ResetOptions as ResetOptionsModel
from services.course_service import CourseService
from services.reset_service import ResetService
from cli.output import format_output, print_error, print_success, print_table

app = typer.Typer(help="Course management commands")
console = Console()


@app.command("list")
def list_courses(
    category_id: Optional[int] = typer.Option(None, "--category-id", "-c", help="Filter by category ID"),
    format: str = typer.Option("table", "--format", help="Output format (table, json, csv)"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output"),
) -> None:
    """List all courses."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            courses = await service.list_courses(category_id)

            if format == "json":
                data = [c.model_dump() for c in courses]
                console.print_json(data=json.dumps(data))
            elif format == "csv":
                import csv
                import sys
                writer = csv.writer(sys.stdout)
                writer.writerow(["ID", "Short Name", "Full Name", "Category ID", "Visible", "Start Date"])
                for c in courses:
                    writer.writerow([
                        c.id,
                        c.shortname,
                        c.fullname,
                        c.categoryid,
                        c.visible,
                        c.startdate.isoformat() if c.startdate else "",
                    ])
            else:
                table = Table(title=f"Courses (Total: {len(courses)})")
                table.add_column("ID", style="cyan")
                table.add_column("Short Name", style="green")
                table.add_column("Full Name")
                table.add_column("Category", style="blue")
                table.add_column("Visible", justify="center")
                if verbose:
                    table.add_column("Start Date")
                    table.add_column("End Date")

                for c in courses:
                    visible = "✓" if c.visible else "✗"
                    visible_style = "green" if c.visible else "red"
                    row = [
                        str(c.id),
                        c.shortname,
                        c.fullname[:50] + "..." if len(c.fullname) > 50 else c.fullname,
                        str(c.categoryid),
                        f"[{visible_style}]{visible}[/]",
                    ]
                    if verbose:
                        row.extend([
                            c.startdate.strftime("%Y-%m-%d") if c.startdate else "",
                            c.enddate.strftime("%Y-%m-%d") if c.enddate else "",
                        ])
                    table.add_row(*row)

                console.print(table)

    asyncio.run(_run())


@app.command("get")
def get_course(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get course details."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                course = await service.get_course(course_id)

                if format == "json":
                    console.print_json(data=json.dumps(course.model_dump()))
                else:
                    from rich.panel import Panel
                    from rich.text import Text

                    content = Text()
                    content.append(f"ID: {course.id}\n", style="bold cyan")
                    content.append(f"Short Name: {course.shortname}\n", style="green")
                    content.append(f"Full Name: {course.fullname}\n")
                    content.append(f"Category ID: {course.categoryid}\n", style="blue")
                    content.append(f"Visible: {'Yes' if course.visible else 'No'}\n")
                    if course.startdate:
                        content.append(f"Start Date: {course.startdate.strftime('%Y-%m-%d')}\n")
                    if course.enddate:
                        content.append(f"End Date: {course.enddate.strftime('%Y-%m-%d')}\n")
                    if course.summary:
                        content.append(f"\nSummary: {course.summary[:200]}...")

                    console.print(Panel(content, title=f"Course {course_id}", border_style="blue"))

            except Exception as e:
                print_error(f"Failed to get course: {e}")

    asyncio.run(_run())


@app.command("create")
def create_course(
    shortname: str = typer.Option(..., "--shortname", "-s", help="Course short name"),
    fullname: str = typer.Option(..., "--fullname", "-f", help="Course full name"),
    category_id: int = typer.Option(..., "--category-id", "-c", help="Category ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Create a new course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                course_data = CourseCreate(
                    shortname=shortname,
                    fullname=fullname,
                    categoryid=category_id,
                )
                course = await service.create_course(course_data)
                print_success(f"Course created successfully with ID: {course.id}")

                if format == "json":
                    console.print_json(data=json.dumps(course.model_dump()))

            except Exception as e:
                print_error(f"Failed to create course: {e}")

    asyncio.run(_run())


@app.command("update")
def update_course(
    course_id: int = typer.Argument(..., help="Course ID"),
    fullname: Optional[str] = typer.Option(None, "--fullname", help="New full name"),
    visible: Optional[bool] = typer.Option(None, "--visible/--hidden", help="Set visibility"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Update a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                update_data = {}
                if fullname is not None:
                    update_data["fullname"] = fullname
                if visible is not None:
                    update_data["visible"] = 1 if visible else 0

                course_update = CourseUpdate(**update_data)
                course = await service.update_course(course_id, course_update)
                print_success(f"Course {course_id} updated successfully")

                if format == "json":
                    console.print_json(data=json.dumps(course.model_dump()))

            except Exception as e:
                print_error(f"Failed to update course: {e}")

    asyncio.run(_run())


@app.command("duplicate")
def duplicate_course(
    course_id: int = typer.Argument(..., help="Source course ID"),
    new_shortname: str = typer.Option(..., "--new-shortname", help="New course short name"),
    new_fullname: str = typer.Option(..., "--new-fullname", help="New course full name"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Duplicate a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                course = await service.duplicate_course(course_id, new_shortname, new_fullname)
                print_success(f"Course duplicated successfully. New ID: {course.id}")

                if format == "json":
                    console.print_json(data=json.dumps(course.model_dump()))

            except Exception as e:
                print_error(f"Failed to duplicate course: {e}")

    asyncio.run(_run())


@app.command("archive")
def archive_course(
    course_id: int = typer.Argument(..., help="Course ID to archive"),
    archive_category: Optional[int] = typer.Option(None, "--category-id", help="Archive category ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without doing it"),
) -> None:
    """Archive a course (hide and move to archive category)."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would archive course {course_id}[/]")
            return

        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                await service.archive_course(course_id, archive_category)
                print_success(f"Course {course_id} archived successfully")
            except Exception as e:
                print_error(f"Failed to archive course: {e}")

    asyncio.run(_run())


@app.command("structure")
def course_structure(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("tree", "--format", help="Output format (tree, json)"),
) -> None:
    """Show course structure with sections and modules."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                structure = await service.get_course_structure(course_id)

                if format == "json":
                    console.print_json(data=json.dumps(structure.model_dump()))
                else:
                    tree = Tree(f"[bold blue]Course {course_id} Structure[/]")
                    for section in structure.sections:
                        section_node = tree.add(
                            f"[green]Section {section.section}:[/] {section.name or 'Untitled'}"
                        )
                        for module in section.modules:
                            visible = "✓" if module.visible else "✗"
                            section_node.add(
                                f"[cyan]{module.modname}[/] {module.name} [dim](ID: {module.id})[/] [{visible}]"
                            )

                    console.print(tree)

            except Exception as e:
                print_error(f"Failed to get course structure: {e}")

    asyncio.run(_run())


@app.command("reset")
def reset_course(
    course_id: int = typer.Argument(..., help="Course ID to reset"),
    reset_grades: bool = typer.Option(False, "--reset-grades", help="Reset grades"),
    reset_completions: bool = typer.Option(False, "--reset-completions", help="Reset completions"),
    reset_submissions: bool = typer.Option(False, "--reset-submissions", help="Reset submissions"),
    reset_quizzes: bool = typer.Option(False, "--reset-quizzes", help="Reset quiz attempts"),
    reset_forums: bool = typer.Option(False, "--reset-forums", help="Delete forum posts"),
    all_options: bool = typer.Option(False, "--all", help="Reset everything"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be reset without doing it"),
) -> None:
    """Reset a course with specified options."""
    async def _run():
        if dry_run:
            console.print("[yellow]DRY RUN: Would reset course with options:[/]")
            if all_options or reset_grades:
                console.print("  - Reset grades")
            if all_options or reset_completions:
                console.print("  - Reset completions")
            if all_options or reset_submissions:
                console.print("  - Reset submissions")
            if all_options or reset_quizzes:
                console.print("  - Reset quiz attempts")
            if all_options or reset_forums:
                console.print("  - Delete forum posts")
            return

        async with AsyncMoodleClient() as client:
            service = ResetService(client)

            options = ResetOptionsModel(
                reset_grades=all_options or reset_grades,
                reset_completion=all_options or reset_completions,
                reset_submissions=all_options or reset_submissions,
                reset_quiz_attempts=all_options or reset_quizzes,
                reset_forum_posts=all_options or reset_forums,
                delete_events=all_options,
                reset_gradebook_items=all_options or reset_grades,
            )

            try:
                result = await service.reset_course(course_id, options)

                if result.status == "success":
                    print_success(f"Course {course_id} reset successfully")
                elif result.status == "partial":
                    console.print(f"[yellow]Course {course_id} partially reset[/]")
                    if result.warnings:
                        for warning in result.warnings:
                            console.print(f"  [dim]Warning: {warning}[/]")
                else:
                    console.print(f"[red]Failed to reset course: {result.message}[/]")

            except Exception as e:
                print_error(f"Failed to reset course: {e}")

    asyncio.run(_run())