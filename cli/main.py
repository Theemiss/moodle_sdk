"""Main CLI entrypoint for moodlectl."""

import asyncio
import logging
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from cli.commands import (
    courses,
    enrollments,
    grades,
    logs,
    progress,
    users,
    content,
    admin,
    categories,
    userfields,
    sql,
)
from config.settings import settings
from utils.logging import setup_logging

# Setup Typer app
app = typer.Typer(
    name="moodlectl",
    help="Headless LMS CLI for Moodle",
    add_completion=False,
)

# Add subcommands
app.add_typer(courses.app, name="courses", help="Course management commands")
app.add_typer(enrollments.app, name="enrollments", help="Enrollment management commands")
app.add_typer(grades.app, name="grades", help="Grade management commands")
app.add_typer(progress.app, name="progress", help="Progress tracking commands")
app.add_typer(users.app, name="users", help="User management commands")
app.add_typer(logs.app, name="logs", help="Activity log commands")
app.add_typer(content.app, name="content", help="Course content management commands")
app.add_typer(admin.app, name="admin", help="System administration commands")
app.add_typer(categories.app, name="categories", help="Course category management commands")
app.add_typer(userfields.app, name="userfields", help="Custom user fields management commands")
app.add_typer(sql.app, name="sql", help="Run custom SQL queries against Moodle database")
console = Console()


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    log_format: Optional[str] = typer.Option(
        None, "--log-format", help="Log format (json or text)"
    ),
) -> None:
    """Global CLI options."""
    # Configure logging
    log_level = logging.DEBUG if verbose else getattr(logging, settings.log_level)
    fmt = log_format if log_format else settings.log_format

    setup_logging(level=log_level, fmt=fmt)

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


def run_async(coro):
    """Helper to run async functions in sync CLI."""
    return asyncio.run(coro)


if __name__ == "__main__":
    app()