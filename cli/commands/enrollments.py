"""Enrollment management CLI commands."""

import asyncio
import csv
import json
import sys  # BUG 2 FIX: was missing — csv format uses sys.stdout
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from client.moodle_client import AsyncMoodleClient
from schemas.enrollment import EnrollmentRequest
from services.enrollment_service import EnrollmentService
from cli.output import print_error, print_success

app = typer.Typer(help="Enrollment management commands")
console = Console()


def _to_json(models) -> str:
    """Serialize Pydantic models to JSON with mode='json' for datetime safety."""
    if isinstance(models, list):
        return json.dumps([m.model_dump(mode="json") for m in models], indent=2)
    return json.dumps(models.model_dump(mode="json"), indent=2)


@app.command("list")
def list_enrollments(
    course_id: int = typer.Argument(..., help="Course ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json, csv"),
) -> None:
    """List all users enrolled in a course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                users = await service.list_enrolled_users(course_id)

                if output_format == "json":
                    console.print_json(_to_json(users))
                elif output_format == "csv":
                    # BUG 2 FIX: sys is now imported — this no longer crashes
                    writer = csv.writer(sys.stdout)
                    writer.writerow(["ID", "Username", "Full Name", "Email", "Roles"])
                    for u in users:
                        writer.writerow([u.id, u.username, u.fullname, u.email, ",".join(u.roles)])
                else:
                    table = Table(title=f"Enrolled Users — Course {course_id} ({len(users)} total)")
                    table.add_column("ID", style="cyan", no_wrap=True)
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
                            ", ".join(u.roles) or "—",
                        )

                    console.print(table)

            except Exception as exc:
                print_error(f"Failed to list enrollments: {exc}")

    asyncio.run(_run())


@app.command("add")
def add_enrollment(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: int = typer.Argument(..., help="Course ID"),
    role_id: int = typer.Option(5, "--role-id", "-r", help="Role ID (5=student, 3=editingteacher)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
) -> None:
    """Enroll a user in a course."""

    async def _run():
        if dry_run:
            console.print(
                f"[yellow]DRY RUN:[/] Would enroll user {user_id} in course {course_id} "
                f"with role_id={role_id}"
            )
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                await service.enroll_user(user_id, course_id, role_id)
                print_success(f"User {user_id} enrolled in course {course_id}")
            except Exception as exc:
                print_error(f"Failed to enroll user: {exc}")

    asyncio.run(_run())


@app.command("remove")
def remove_enrollment(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: int = typer.Argument(..., help="Course ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
) -> None:
    """Unenroll a user from a course."""

    async def _run():
        if dry_run:
            console.print(
                f"[yellow]DRY RUN:[/] Would unenroll user {user_id} from course {course_id}"
            )
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                await service.unenroll_user(user_id, course_id)
                print_success(f"User {user_id} unenrolled from course {course_id}")
            except Exception as exc:
                print_error(f"Failed to unenroll user: {exc}")

    asyncio.run(_run())


@app.command("bulk")
def bulk_enroll(
    file: str = typer.Option(..., "--file", "-f", help="CSV file (columns: user_id, course_id, role_id)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
) -> None:
    """Bulk enroll users from a CSV file."""

    async def _run():
        enrollments: List[EnrollmentRequest] = []
        try:
            with open(file, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    enrollments.append(
                        EnrollmentRequest(
                            user_id=int(row["user_id"]),
                            course_id=int(row["course_id"]),
                            role_id=int(row.get("role_id", 5)),
                        )
                    )
        except (OSError, KeyError, ValueError) as exc:
            print_error(f"Failed to read CSV file: {exc}")
            return

        if dry_run:
            console.print(f"[yellow]DRY RUN:[/] Would enroll {len(enrollments)} users")
            for req in enrollments[:5]:
                console.print(
                    f"  User {req.user_id} → course {req.course_id} (role {req.role_id})"
                )
            if len(enrollments) > 5:
                console.print(f"  [dim]... and {len(enrollments) - 5} more[/]")
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)
            try:
                result = await service.bulk_enroll(enrollments)
                if result.failed == 0:
                    print_success(f"Enrolled {result.succeeded} users successfully")
                else:
                    console.print(
                        f"[yellow]Partial success:[/] {result.succeeded} enrolled, "
                        f"{result.failed} failed"
                    )
                    for uid, cid, error in result.failures[:5]:
                        console.print(f"  [dim]User {uid} → course {cid}: {error}[/]")
            except Exception as exc:
                print_error(f"Bulk enroll failed: {exc}")

    asyncio.run(_run())


@app.command("sync")
def sync_enrollments(
    course_id: int = typer.Argument(..., help="Course ID"),
    file: str = typer.Option(..., "--file", "-f", help="CSV with expected enrollments"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
) -> None:
    """Sync enrollments to match the expected state from a CSV file."""

    async def _run():
        expected: List[EnrollmentRequest] = []
        try:
            with open(file, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    expected.append(
                        EnrollmentRequest(
                            user_id=int(row["user_id"]),
                            course_id=course_id,
                            role_id=int(row.get("role_id", 5)),
                        )
                    )
        except (OSError, KeyError, ValueError) as exc:
            print_error(f"Failed to read CSV file: {exc}")
            return

        async with AsyncMoodleClient() as client:
            service = EnrollmentService(client)

            if dry_run:
                current = await service.list_enrolled_users(course_id)
                current_ids = {u.id for u in current}
                expected_ids = {req.user_id for req in expected}
                to_add = expected_ids - current_ids
                to_remove = current_ids - expected_ids

                console.print("[yellow]DRY RUN:[/] Sync would:")
                console.print(f"  Add    {len(to_add)} enrollments")
                console.print(f"  Remove {len(to_remove)} enrollments")
                console.print(f"  Keep   {len(current_ids & expected_ids)} unchanged")
                return

            try:
                result = await service.sync_enrollments(course_id, expected)

                status = "[green]Sync complete[/]" if not result.errors else "[yellow]Sync complete with errors[/]"
                console.print(status)
                console.print(f"  Added:     {result.added}")
                console.print(f"  Removed:   {result.removed}")
                console.print(f"  Unchanged: {result.unchanged}")

                if result.errors:
                    console.print(f"\n[yellow]{len(result.errors)} error(s):[/]")
                    for err in result.errors[:5]:
                        console.print(f"  [dim]{err}[/]")

            except Exception as exc:
                print_error(f"Sync failed: {exc}")

    asyncio.run(_run())