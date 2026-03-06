"""CLI output formatting utilities."""

from datetime import datetime
import sys
from typing import Any, Dict, List, Optional

from rich import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit."""
    # Use print with stderr for errors
    console = Console(stderr=True)
    console.print(f"[red]Error:[/] {message}")
    sys.exit(exit_code)


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/] {message}")


def print_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    title: Optional[str] = None,
) -> None:
    """
    Print data as a rich table.

    Args:
        data: List of dictionaries with data
        columns: List of column names (if None, use keys from first item)
        title: Optional table title
    """
    if not data:
        console.print("[dim]No data to display[/]")
        return

    if columns is None:
        columns = list(data[0].keys())

    table = Table(title=title)
    for col in columns:
        table.add_column(col.replace("_", " ").title())

    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    import json
    console.print_json(data=json.dumps(data))


def format_output(data: Any, fmt: str = "table") -> None:
    """
    Format and print data based on format specifier.

    Args:
        data: Data to print
        fmt: Format type (table, json, csv)
    """
    if fmt == "json":
        print_json(data)
    elif fmt == "table" and isinstance(data, list) and data:
        print_table(data)
    elif fmt == "table" and isinstance(data, dict):
        # Single item as panel
        content = Text()
        for key, value in data.items():
            content.append(f"{key}: {value}\n")
        console.print(Panel(content))
    else:
        console.print(data)
        
        
        
        
        
        
        
        
def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def print_json_data(data):
    """Print data as formatted JSON with proper datetime handling."""
    console.print_json(data=json.dumps(data, default=json_serializer))