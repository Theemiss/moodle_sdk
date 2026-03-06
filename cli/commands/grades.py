"""Grade management CLI commands."""

import asyncio
import csv
import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from analytics.grade_analytics import compute_grade_distribution, compute_student_performance
from cli.output import print_error
from client.moodle_client import AsyncMoodleClient
from services.grade_service import GradeService

app = typer.Typer(help="Grade management commands")
console = Console()


def _to_json(obj) -> str:
    """
    BUG 8 FIX: Serialize Pydantic model(s) to JSON safely.

    The original code used json.dumps(report.model_dump()) and
    json.dumps([r.model_dump() for r in reports]) throughout this file.
    model_dump() without mode='json' returns datetime objects which
    json.dumps() cannot serialize, raising:
        TypeError: Object of type datetime is not JSON serializable

    Fix: use model_dump(mode='json') everywhere.
    """
    if isinstance(obj, list):
        return json.dumps([m.model_dump(mode="json") for m in obj], indent=2)
    return json.dumps(obj.model_dump(mode="json"), indent=2)


def _fmt_pct(value: Optional[float]) -> str:
    """
    BUG 3 FIX: Format a percentage value that has already been parsed to float.

    GradeService._parse_percentage() converts Moodle's "75.00 %" strings to
    float before storing in the schema. This function safely formats that float.
    Previously the CLI tried f"{grade.percentage:.1f}%" directly on the raw
    Moodle string, causing:
        ValueError: Unknown format code 'f' for object of type 'str'
    """
    if value is None:
        return "—"
    return f"{value:.1f}%"


@app.command("report")
def grade_report(
    course_id: int = typer.Argument(..., help="Course ID"),
    user_id: Optional[int] = typer.Option(None, "--user-id", "-u", help="Single user ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json, csv"),
) -> None:
    """Get grade report for a course or a specific user."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = GradeService(client)
            try:
                if user_id:
                    report = await service.get_user_grades(user_id, course_id)

                    if output_format == "json":
                        console.print_json(_to_json(report))   # BUG 8 FIX
                    elif output_format == "csv":
                        writer = csv.writer(sys.stdout)
                        writer.writerow(["Grade Item", "Grade", "Percentage", "Letter"])
                        for grade in report.grades:
                            item = next(
                                (g for g in report.grade_items if g.id == grade.grade_item_id), None
                            )
                            writer.writerow([
                                item.itemname if item else "—",
                                grade.grade if grade.grade is not None else "—",
                                _fmt_pct(grade.percentage),   # BUG 3 FIX
                                grade.lettergrade or "—",
                            ])
                    else:
                        console.print(
                            f"[bold]Grade Report — {report.user_fullname} | Course {course_id}[/]\n"
                        )
                        table = Table()
                        table.add_column("Grade Item")
                        table.add_column("Grade", justify="right")
                        table.add_column("Percentage", justify="right")
                        table.add_column("Letter", justify="center")

                        for grade in report.grades:
                            item = next(
                                (g for g in report.grade_items if g.id == grade.grade_item_id), None
                            )
                            table.add_row(
                                item.itemname if item else "—",
                                str(grade.grade) if grade.grade is not None else "—",
                                _fmt_pct(grade.percentage),   # BUG 3 FIX
                                grade.lettergrade or "—",
                            )
                        console.print(table)

                        if report.total_grade is not None:
                            console.print(f"\n[bold]Total:[/] {report.total_grade}")

                else:
                    reports = await service.get_course_grades(course_id)

                    if output_format == "json":
                        console.print_json(_to_json(reports))   # BUG 8 FIX
                    elif output_format == "csv":
                        writer = csv.writer(sys.stdout)
                        writer.writerow(["User ID", "Name", "Grade", "Percentage"])
                        for r in reports:
                            writer.writerow([
                                r.user_id,
                                r.user_fullname,
                                r.total_grade if r.total_grade is not None else "—",
                                _fmt_pct(getattr(r, "total_percentage", None)),
                            ])
                    else:
                        table = Table(title=f"Grade Report — Course {course_id} ({len(reports)} students)")
                        table.add_column("User ID", style="cyan", no_wrap=True)
                        table.add_column("Name")
                        table.add_column("Grade", justify="right")
                        table.add_column("Percentage", justify="right")

                        for r in reports:
                            table.add_row(
                                str(r.user_id),
                                r.user_fullname,
                                str(r.total_grade) if r.total_grade is not None else "—",
                                _fmt_pct(getattr(r, "total_percentage", None)),
                            )
                        console.print(table)

            except Exception as exc:
                print_error(f"Failed to get grade report: {exc}")

    asyncio.run(_run())


@app.command("distribution")
def grade_distribution(
    course_id: int = typer.Argument(..., help="Course ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Show grade distribution statistics for a course."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = GradeService(client)
            try:
                reports = await service.get_course_grades(course_id)
                distribution = compute_grade_distribution(reports)

                if output_format == "json":
                    console.print_json(_to_json(distribution))   # BUG 8 FIX
                    return

                console.print(f"[bold]Grade Distribution — Course {course_id}[/]\n")
                console.print(f"Students:  {distribution.total_students}")
                console.print(f"Mean:      {distribution.mean:.2f}%")
                console.print(f"Median:    {distribution.median:.2f}%")
                console.print(f"Std Dev:   {distribution.std_dev:.2f}")
                console.print(f"Pass Rate: {distribution.pass_rate * 100:.1f}%")

                console.print("\n[bold]Percentiles:[/]")
                for p, val in distribution.percentiles.items():
                    console.print(f"  p{p}: {val:.1f}%")

                console.print("\n[bold]Grade Buckets:[/]")
                total = distribution.total_students or 1
                for bucket, count in distribution.grade_buckets.items():
                    pct = count / total * 100
                    bar = "█" * int(pct / 2)  # 50-char max bar
                    console.print(f"  {bucket:>3}  {bar:<25} {count:>3} ({pct:.1f}%)")

            except Exception as exc:
                print_error(f"Failed to compute grade distribution: {exc}")

    asyncio.run(_run())


@app.command("performance")
def student_performance(
    course_id: int = typer.Argument(..., help="Course ID"),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Show ranked student performance with z-scores and percentile bands."""

    async def _run():
        async with AsyncMoodleClient() as client:
            service = GradeService(client)
            try:
                reports = await service.get_course_grades(course_id)
                performances = compute_student_performance(reports)

                if output_format == "json":
                    console.print_json(_to_json(performances))   # BUG 8 FIX
                    return

                table = Table(
                    title=f"Student Performance — Course {course_id} ({len(performances)} students)"
                )
                table.add_column("Rank", justify="right", style="cyan", no_wrap=True)
                table.add_column("Student")
                table.add_column("Grade", justify="right")
                table.add_column("Z-Score", justify="right")
                table.add_column("Percentile", justify="right")
                table.add_column("Band", justify="center")

                BAND_STYLES = {"A": "green", "B": "cyan", "C": "yellow", "D": "orange3", "F": "red"}

                for rank, p in enumerate(performances, 1):
                    style = BAND_STYLES.get(p.performance_band, "white")
                    table.add_row(
                        str(rank),
                        p.user_fullname,
                        _fmt_pct(p.grade),          # BUG 3 FIX: p.grade is already float
                        f"{p.z_score:.2f}",
                        _fmt_pct(p.percentile_rank),
                        f"[{style}]{p.performance_band}[/]",
                    )

                console.print(table)

            except Exception as exc:
                print_error(f"Failed to analyze student performance: {exc}")

    asyncio.run(_run())