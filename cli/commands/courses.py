"""Course management CLI commands."""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from client.moodle_client import AsyncMoodleClient
from schemas.course import CourseCreate, CourseUpdate
from schemas.reset import ResetOptions as ResetOptionsModel
from services.course_service import CourseService
from services.reset_service import ResetService
from cli.output import print_error, print_success

app = typer.Typer(help="Course management commands")
console = Console()


def _json_serial(obj):
    """
    BUG 8 FIX: json.dumps() raises TypeError on datetime objects.

    The original code called:
        json.dumps(course.model_dump())

    model_dump() without mode='json' returns Python-native types, including
    datetime objects, which are NOT JSON-serializable. This caused:

        TypeError: Object of type datetime is not JSON serializable

    Fix: use model_dump(mode='json') which converts all types to JSON-safe
    equivalents (datetimes → ISO strings, etc.) before passing to json.dumps().

    This fallback serializer handles any remaining edge cases from other models.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} is not JSON serializable")


def _to_json(model) -> str:
    """Serialize a Pydantic model to a JSON string safely."""
    return json.dumps(model.model_dump(mode="json"), indent=2)


@app.command("list")
def list_courses(
    category_id: Optional[int] = typer.Option(None, "--category-id", "-c", help="Filter by category ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json, csv"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extended fields"),
) -> None:
    """List all courses."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            courses = await service.list_courses(category_id)

            if output_format == "json":
                data = [c.model_dump(mode="json") for c in courses]
                console.print_json(json.dumps(data))

            elif output_format == "csv":
                import csv
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
                table = Table(title=f"Courses ({len(courses)} total)")
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Short Name", style="green")
                table.add_column("Full Name")
                table.add_column("Category", style="blue", justify="right")
                table.add_column("Visible", justify="center")
                if verbose:
                    table.add_column("Start Date")
                    table.add_column("End Date")

                for c in courses:
                    visible_icon = "[green]✓[/]" if c.visible else "[red]✗[/]"
                    name = c.fullname if len(c.fullname) <= 50 else c.fullname[:47] + "..."
                    row = [str(c.id), c.shortname, name, str(c.categoryid), visible_icon]
                    if verbose:
                        row += [
                            c.startdate.strftime("%Y-%m-%d") if c.startdate else "—",
                            c.enddate.strftime("%Y-%m-%d") if c.enddate else "—",
                        ]
                    table.add_row(*row)

                console.print(table)

    asyncio.run(_run())


@app.command("get")
def get_course(
    course_id: int = typer.Argument(..., help="Course ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Get detailed information for a single course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                course = await service.get_course(course_id)

                if output_format == "json":
                    console.print_json(_to_json(course))
                else:
                    content = Text()
                    content.append(f"ID:          {course.id}\n", style="bold cyan")
                    content.append(f"Short Name:  {course.shortname}\n", style="green")
                    content.append(f"Full Name:   {course.fullname}\n")
                    content.append(f"Category ID: {course.categoryid}\n", style="blue")
                    content.append(f"Visible:     {'Yes' if course.visible else 'No'}\n")
                    if course.startdate:
                        content.append(f"Start Date:  {course.startdate.strftime('%Y-%m-%d')}\n")
                    if course.enddate:
                        content.append(f"End Date:    {course.enddate.strftime('%Y-%m-%d')}\n")
                    if course.summary:
                        summary = course.summary[:200] + ("..." if len(course.summary) > 200 else "")
                        content.append(f"\nSummary:\n{summary}")

                    console.print(Panel(content, title=f"[bold]Course {course_id}[/]", border_style="blue"))

            except Exception as exc:
                print_error(f"Failed to get course {course_id}: {exc}")

    asyncio.run(_run())


@app.command("create")
def create_course(
    shortname: str = typer.Option(..., "--shortname", "-s", help="Course short name (unique)"),
    fullname: str = typer.Option(..., "--fullname", "-f", help="Course full name"),
    category_id: int = typer.Option(..., "--category-id", "-c", help="Category ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Create a new course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                course = await service.create_course(
                    CourseCreate(shortname=shortname, fullname=fullname, categoryid=category_id)
                )
                print_success(f"Course created — ID: {course.id}, Short name: {course.shortname}")
                if output_format == "json":
                    console.print_json(_to_json(course))
            except Exception as exc:
                print_error(f"Failed to create course: {exc}")

    asyncio.run(_run())


@app.command("update")
def update_course(
    course_id: int = typer.Argument(..., help="Course ID"),
    fullname: Optional[str] = typer.Option(None, "--fullname", help="New full name"),
    visible: Optional[bool] = typer.Option(None, "--visible/--hidden", help="Set visibility"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Update an existing course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                fields: dict = {}
                if fullname is not None:
                    fields["fullname"] = fullname
                if visible is not None:
                    fields["visible"] = 1 if visible else 0

                if not fields:
                    print_error("No update fields provided. Use --fullname or --visible/--hidden.")

                course = await service.update_course(course_id, CourseUpdate(**fields))
                print_success(f"Course {course_id} updated successfully")
                if output_format == "json":
                    console.print_json(_to_json(course))
            except Exception as exc:
                print_error(f"Failed to update course {course_id}: {exc}")

    asyncio.run(_run())


@app.command("duplicate")
def duplicate_course(
    course_id: int = typer.Argument(..., help="Source course ID"),
    new_shortname: str = typer.Option(..., "--new-shortname", help="Short name for the new course"),
    new_fullname: str = typer.Option(..., "--new-fullname", help="Full name for the new course"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Duplicate a course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                course = await service.duplicate_course(course_id, new_shortname, new_fullname)
                print_success(f"Course duplicated — New ID: {course.id}")
                if output_format == "json":
                    console.print_json(_to_json(course))
            except Exception as exc:
                print_error(f"Failed to duplicate course {course_id}: {exc}")

    asyncio.run(_run())


@app.command("archive")
def archive_course(
    course_id: int = typer.Argument(..., help="Course ID to archive"),
    archive_category: Optional[int] = typer.Option(None, "--category-id", help="Move to this category ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
) -> None:
    """Archive a course (hide and optionally move to an archive category)."""

    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN:[/] Would archive course {course_id}")
            if archive_category:
                console.print(f"         Would move to category {archive_category}")
            return

        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                await service.archive_course(course_id, archive_category)
                print_success(f"Course {course_id} archived")
            except Exception as exc:
                print_error(f"Failed to archive course {course_id}: {exc}")

    asyncio.run(_run())


@app.command("structure")
def course_structure(
    course_id: int = typer.Argument(..., help="Course ID"),
    output_format: str = typer.Option("tree", "--format", help="Output format: tree, json"),
) -> None:
    """Show course structure (sections and activities)."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = CourseService(client)
            try:
                structure = await service.get_course_structure(course_id)

                if output_format == "json":
                    console.print_json(_to_json(structure))
                else:
                    tree = Tree(f"[bold blue]Course {course_id}[/]")
                    for section in structure.sections:
                        label = section.name or f"Section {section.section}"
                        section_node = tree.add(f"[green]{label}[/]")
                        for module in section.modules:
                            status = "✓" if module.visible else "✗"
                            section_node.add(
                                f"[cyan]{module.modname}[/]  {module.name}  "
                                f"[dim](id={module.id}) [{status}][/]"
                            )
                    console.print(tree)

            except Exception as exc:
                print_error(f"Failed to get structure for course {course_id}: {exc}")

    asyncio.run(_run())


@app.command("reset")
def reset_course(
    course_id: int = typer.Argument(..., help="Course ID to reset"),
    reset_grades: bool = typer.Option(False, "--reset-grades", help="Reset all grades"),
    reset_completions: bool = typer.Option(False, "--reset-completions", help="Reset completion data"),
    reset_submissions: bool = typer.Option(False, "--reset-submissions", help="Reset assignment submissions"),
    reset_quizzes: bool = typer.Option(False, "--reset-quizzes", help="Reset quiz attempts"),
    reset_forums: bool = typer.Option(False, "--reset-forums", help="Delete forum posts"),
    all_options: bool = typer.Option(False, "--all", help="Reset everything"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
) -> None:
    """Reset a course with the specified options."""

    async def _run():
        effective = {
            "grades": all_options or reset_grades,
            "completions": all_options or reset_completions,
            "submissions": all_options or reset_submissions,
            "quizzes": all_options or reset_quizzes,
            "forums": all_options or reset_forums,
        }

        if dry_run:
            console.print(f"[yellow]DRY RUN:[/] Would reset course {course_id} with:")
            for label, active in effective.items():
                icon = "[green]✓[/]" if active else "[dim]✗[/]"
                console.print(f"  {icon} {label}")
            return

        if not any(effective.values()):
            print_error("No reset options selected. Use --reset-grades, --all, etc.")

        async with AsyncMoodleClient() as client:
            service = ResetService(client)
            options = ResetOptionsModel(
                reset_grades=effective["grades"],
                reset_gradebook_items=effective["grades"],
                reset_completion=effective["completions"],
                reset_submissions=effective["submissions"],
                reset_quiz_attempts=effective["quizzes"],
                reset_forum_posts=effective["forums"],
                delete_events=all_options,
            )
            try:
                result = await service.reset_course(course_id, options)
                if result.status == "success":
                    print_success(f"Course {course_id} reset successfully")
                elif result.status == "partial":
                    console.print(f"[yellow]⚠[/] Course {course_id} partially reset")
                    for w in (result.warnings or []):
                        console.print(f"  [dim]Warning: {w}[/]")
                else:
                    console.print(f"[red]✗[/] Reset failed: {result.message}")
            except Exception as exc:
                print_error(f"Failed to reset course {course_id}: {exc}")

    asyncio.run(_run())