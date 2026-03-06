"""User management CLI commands."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from client.moodle_client import AsyncMoodleClient
from schemas.user import UserSearchQuery
from services.user_service import UserService
from cli.output import print_error, print_success

app = typer.Typer(help="User management commands")
console = Console()


@app.command("get")
def get_user(
    user_id: int = typer.Argument(..., help="User ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get user details by ID."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserService(client)

            try:
                user = await service.get_user(user_id)

                if format == "json":
                    console.print_json(data=json.dumps(user.model_dump()))
                else:
                    content = f"""
[bold cyan]User ID:[/] {user.id}
[bold green]Username:[/] {user.username}
[bold]Full Name:[/] {user.fullname}
[bold]Email:[/] {user.email}
[bold]ID Number:[/] {user.idnumber or 'N/A'}
[bold]Institution:[/] {user.institution or 'N/A'}
[bold]Department:[/] {user.department or 'N/A'}

[bold]Status:[/] {'[red]Suspended[/]' if user.suspended else '[green]Active[/]'}
[bold]Auth Method:[/] {user.auth}
[bold]Language:[/] {user.lang}
[bold]Timezone:[/] {user.timezone}

[bold]Access:[/]
  First Access: {user.firstaccess.strftime('%Y-%m-%d %H:%M') if user.firstaccess else 'Never'}
  Last Access: {user.lastaccess.strftime('%Y-%m-%d %H:%M') if user.lastaccess else 'Never'}
  Last Login: {user.lastlogin.strftime('%Y-%m-%d %H:%M') if user.lastlogin else 'Never'}
"""

                    if user.roles:
                        content += "\n[bold]Roles:[/]\n"
                        for role in user.roles:
                            content += f"  - {role.name} ({role.shortname})\n"

                    console.print(Panel(content, title=f"User {user_id}", border_style="blue"))

            except Exception as e:
                print_error(f"Failed to get user: {e}")

    asyncio.run(_run())


@app.command("search")
def search_users(
    query: str = typer.Option(..., "--query", "-q", help="Search query"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Search for users."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserService(client)

            try:
                search_query = UserSearchQuery(query=query, limit=limit)
                users = await service.search_users(search_query)

                if format == "json":
                    data = [u.model_dump() for u in users]
                    console.print_json(data=json.dumps(data))
                else:
                    table = Table(title=f"Search Results for '{query}'")
                    table.add_column("ID", style="cyan")
                    table.add_column("Username", style="green")
                    table.add_column("Full Name")
                    table.add_column("Email")
                    table.add_column("Status", justify="center")

                    for user in users:
                        status = "[red]Suspended[/]" if user.suspended else "[green]Active[/]"
                        table.add_row(
                            str(user.id),
                            user.username,
                            user.fullname,
                            user.email,
                            status,
                        )

                    console.print(table)
                    console.print(f"\n[dim]Total: {len(users)} users[/]")

            except Exception as e:
                print_error(f"Failed to search users: {e}")

    asyncio.run(_run())


@app.command("find-by-email")
def find_by_email(
    email: str = typer.Argument(..., help="Email address"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Find user by email address."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserService(client)

            try:
                user = await service.get_user_by_email(email)

                if not user:
                    console.print(f"[yellow]No user found with email: {email}[/]")
                    return

                if format == "json":
                    console.print_json(data=json.dumps(user.model_dump()))
                else:
                    console.print(f"[bold green]Found:[/] {user.fullname} (ID: {user.id})")
                    console.print(f"Username: {user.username}")
                    console.print(f"Status: {'Active' if not user.suspended else 'Suspended'}")

            except Exception as e:
                print_error(f"Failed to find user: {e}")

    asyncio.run(_run())


@app.command("roles")
def user_roles(
    user_id: int = typer.Argument(..., help="User ID"),
    course_id: int = typer.Option(..., "--course-id", "-c", help="Course ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get user's roles in a course."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserService(client)

            try:
                roles = await service.get_user_roles(user_id, course_id)

                if format == "json":
                    console.print_json(data=json.dumps(roles))
                else:
                    if roles:
                        console.print(f"[bold]User {user_id} roles in course {course_id}:[/]")
                        for role in roles:
                            console.print(f"  - {role}")
                    else:
                        console.print(f"[yellow]User {user_id} has no roles in course {course_id}[/]")

            except Exception as e:
                print_error(f"Failed to get user roles: {e}")

    asyncio.run(_run())