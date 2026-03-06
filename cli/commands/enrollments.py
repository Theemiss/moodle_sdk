"""Enrollment management CLI commands."""

import asyncio
import csv
import json
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from client.moodle_client import AsyncMoodleClient
from schemas.enrollment import EnrollmentRequest
from services.enrollment_service import EnrollmentService
from cli.output import print_error, print_success, print_table

app = typer.Typer(help="Enrollment management commands")
console = Console()


@app.command("list")
def list_enrollments(
    course_id: int = typer.Argument(..., help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List all users enrolled in a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                users = await service.list_enrolled_users(course_id)

                if format == "json":
                    data = [u.model_dump() for u in users]
                    console.print_json(data=json.dumps(data))
                elif format == "csv":
                    writer = csv.writer(sys.stdout)
                    writer.writerow(["ID", "Username", "Full Name", "Email", "Roles"])
                    for u in users:
                        writer.writerow([u.id, u.username, u.fullname, u.email, ",".join(u.roles)])
                else:
                    table = Table(title=f"Enrolled Users in Course {course_id}")
                    table.add_column("ID", style="cyan")
                    table.add_column("Username", style="green")
                    table.add_column("Full Name")
                    table.add_column("Email")
                    table.add_column("Roles")

                    for u in users:
                        table.add_row(
                            str(u.id),
                            u.username,
                            u.fullname,
                            u.email,
                            ", ".join(u.roles),
                        )

                    console.print(table)

            except Exception as e:
                print_error(f"Failed to list enrollments: {e}")

    asyncio.run(_run())


@app.command("add")
def add_enrollment(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: int = typer.Argument(..., help="Course ID"),
    role_id: int = typer.Option(5, "--role-id", "-r", help="Role ID (5=student, 3=teacher)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Enroll a user in a course."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would enroll user {user_id} in course {course_id} with role {role_id}[/]")
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                await service.enroll_user(user_id, course_id, role_id)
                print_success(f"User {user_id} enrolled in course {course_id}")
            except Exception as e:
                print_error(f"Failed to enroll user: {e}")

    asyncio.run(_run())


@app.command("remove")
def remove_enrollment(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: int = typer.Argument(..., help="Course ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Unenroll a user from a course."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would unenroll user {user_id} from course {course_id}[/]")
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                await service.unenroll_user(user_id, course_id)
                print_success(f"User {user_id} unenrolled from course {course_id}")
            except Exception as e:
                print_error(f"Failed to unenroll user: {e}")

    asyncio.run(_run())


@app.command("bulk")
def bulk_enroll(
    file: str = typer.Option(..., "--file", "-f", help="CSV file with enrollments"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Bulk enroll users from a CSV file."""
    async def _run():
        enrollments = []

        # Read CSV file
        try:
            with open(file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    enrollments.append(
                        EnrollmentRequest(
                            user_id=int(row["user_id"]),
                            course_id=int(row["course_id"]),
                            role_id=int(row.get("role_id", 5)),
                        )
                    )
        except Exception as e:
            print_error(f"Failed to read CSV file: {e}")
            return

        if dry_run:
            console.print(f"[yellow]DRY RUN: Would enroll {len(enrollments)} users[/]")
            for e in enrollments[:5]:  # Show first 5
                console.print(f"  - User {e.user_id} in course {e.course_id} (role {e.role_id})")
            if len(enrollments) > 5:
                console.print(f"  ... and {len(enrollments) - 5} more")
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                result = await service.bulk_enroll(enrollments)

                if result.failed == 0:
                    print_success(f"Successfully enrolled {result.succeeded} users")
                else:
                    console.print(
                        f"[yellow]Partial success: {result.succeeded} enrolled, {result.failed} failed[/]"
                    )
                    for user_id, course_id, error in result.failures[:5]:
                        console.print(f"  [dim]User {user_id} in course {course_id}: {error}[/]")

            except Exception as e:
                print_error(f"Failed to bulk enroll: {e}")

    asyncio.run(_run())


@app.command("sync")
def sync_enrollments(
    course_id: int = typer.Argument(..., help="Course ID"),
    file: str = typer.Option(..., "--file", "-f", help="CSV file with expected enrollments"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Sync enrollments to match expected state from CSV."""
    async def _run():
        expected = []

        try:
            with open(file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    expected.append(
                        EnrollmentRequest(
                            user_id=int(row["user_id"]),
                            course_id=course_id,
                            role_id=int(row.get("role_id", 5)),
                        )
                    )
        except Exception as e:
            print_error(f"Failed to read CSV file: {e}")
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)

            if dry_run:
                # Get current enrollments for comparison
                current = await service.list_enrolled_users(course_id)
                current_set = {(u.id, 5) for u in current}  # TODO: Handle roles properly
                expected_set = {(e.user_id, e.role_id) for e in expected}

                to_remove = current_set - expected_set
                to_add = expected_set - current_set

                console.print("[yellow]DRY RUN: Enrollment sync would:[/]")
                console.print(f"  - Add {len(to_add)} enrollments")
                console.print(f"  - Remove {len(to_remove)} enrollments")
                console.print(f"  - Keep {len(current_set & expected_set)} unchanged")
                return

            try:
                result = await service.sync_enrollments(course_id, expected)

                if result.errors:
                    console.print(f"[yellow]Sync completed with {len(result.errors)} errors:[/]")
                    for error in result.errors[:5]:
                        console.print(f"  [dim]{error}[/]")

                console.print(f"[green]Sync complete:[/]")
                console.print(f"  Added: {result.added}")
                console.print(f"  Removed: {result.removed}")
                console.print(f"  Unchanged: {result.unchanged}")

            except Exception as e:
                print_error(f"Failed to sync enrollments: {e}")

    asyncio.run(_run())