"""Output parser for SQL query results with multiple format support."""

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.table import Table as RichTable
from rich.text import Text


class OutputFormat(str, Enum):
    """Supported output formats."""
    JSON = "json"
    CSV = "csv"
    TABLE = "table"
    RAW = "raw"
    COMPACT = "compact"


class QueryOutputParser:
    """
    Parser for formatting SQL query results in various output formats.
    
    Supported formats:
    - JSON: Pretty-printed JSON
    - CSV: Comma-separated values
    - TABLE: Rich formatted table
    - RAW: Raw Python objects (for programmatic use)
    - COMPACT: Compact table format
    """
    
    def __init__(self):
        self.console = Console()
    
    def format(
        self,
        data: Union[List[Dict[str, Any]], Dict[str, Any], Any],
        output_format: Union[str, OutputFormat] = OutputFormat.TABLE
    ) -> Union[str, List[Dict], Dict]:
        """
        Format data according to the specified output format.
        
        Args:
            data: Data to format (list of dicts, dict, or scalar)
            output_format: Desired output format
            
        Returns:
            Formatted data as string or Python objects
        """
        # Convert string format to enum
        if isinstance(output_format, str):
            try:
                output_format = OutputFormat(output_format.lower())
            except ValueError:
                output_format = OutputFormat.TABLE
        
        # Handle empty data
        if data is None or (isinstance(data, (list, dict)) and len(data) == 0):
            return self._format_empty(output_format)
        
        # Convert to list if single dict
        if isinstance(data, dict):
            data = [data]
        
        # Format based on type
        if output_format == OutputFormat.JSON:
            return self._format_json(data)
        elif output_format == OutputFormat.CSV:
            return self._format_csv(data)
        elif output_format == OutputFormat.TABLE:
            return self._format_table(data)
        elif output_format == OutputFormat.COMPACT:
            return self._format_compact(data)
        elif output_format == OutputFormat.RAW:
            return data
        else:
            return self._format_table(data)
    
    def _format_json(self, data: List[Dict[str, Any]]) -> str:
        """Format as pretty-printed JSON."""
        def json_serializer(obj: Any) -> str:
            """Handle non-serializable types."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, bytes):
                return obj.decode('utf-8', errors='replace')
            raise TypeError(f"Type {type(obj)} not serializable")
        
        return json.dumps(
            data,
            indent=2,
            default=json_serializer,
            ensure_ascii=False
        )
    
    def _format_csv(self, data: List[Dict[str, Any]]) -> str:
        """Format as CSV."""
        if not data:
            return ""
        
        output = io.StringIO()
        
        # Get all possible column names
        fieldnames = set()
        for row in data:
            fieldnames.update(row.keys())
        fieldnames = sorted(fieldnames)
        
        # Write CSV
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for row in data:
            # Convert complex types to strings
            clean_row = {}
            for key, value in row.items():
                if isinstance(value, (datetime, date)):
                    clean_row[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    clean_row[key] = json.dumps(value, default=str)
                elif isinstance(value, Decimal):
                    clean_row[key] = float(value)
                elif isinstance(value, bytes):
                    clean_row[key] = value.decode('utf-8', errors='replace')
                else:
                    clean_row[key] = value
            writer.writerow(clean_row)
        
        return output.getvalue()
    
    def _format_table(self, data: List[Dict[str, Any]]) -> str:
        """Format as rich table."""
        if not data:
            return "No results"
        
        # Create rich table
        table = RichTable(show_header=True, header_style="bold magenta")
        
        # Get columns from first row
        columns = list(data[0].keys())
        
        # Add columns
        for col in columns:
            table.add_column(col, overflow="fold")
        
        # Add rows
        for row in data:
            table.add_row(*[self._format_cell_value(row.get(col, "")) for col in columns])
        
        # Render table
        with self.console.capture() as capture:
            self.console.print(table)
        
        return capture.get()
    
    def _format_compact(self, data: List[Dict[str, Any]]) -> str:
        """Format as compact table (minimal borders)."""
        if not data:
            return "No results"
        
        # Get columns
        columns = list(data[0].keys())
        
        # Calculate column widths
        col_widths = {col: len(col) for col in columns}
        for row in data:
            for col in columns:
                value = self._format_cell_value(row.get(col, ""))
                col_widths[col] = max(col_widths[col], len(str(value)))
        
        # Build separator
        separator = "+-" + "-+-".join(["-" * col_widths[col] for col in columns]) + "-+"
        
        lines = []
        
        # Header
        lines.append(separator)
        header = "| " + " | ".join([col.ljust(col_widths[col]) for col in columns]) + " |"
        lines.append(header)
        lines.append(separator.replace("-", "="))
        
        # Rows
        for row in data:
            row_str = "| " + " | ".join([
                str(self._format_cell_value(row.get(col, ""))).ljust(col_widths[col])
                for col in columns
            ]) + " |"
            lines.append(row_str)
        
        # Footer
        lines.append(separator)
        
        return "\n".join(lines)
    
    def _format_empty(self, output_format: OutputFormat) -> Union[str, List]:
        """Format empty result set."""
        if output_format == OutputFormat.JSON:
            return json.dumps({"message": "No results found", "count": 0}, indent=2)
        elif output_format == OutputFormat.CSV:
            return ""
        elif output_format in (OutputFormat.TABLE, OutputFormat.COMPACT):
            return "No results found"
        elif output_format == OutputFormat.RAW:
            return []
        else:
            return "No results"
    
    def _format_cell_value(self, value: Any) -> str:
        """Format a single cell value for display."""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return str(value).upper()
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        elif isinstance(value, Decimal):
            return str(float(value))
        elif isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        elif isinstance(value, float):
            return f"{value:.2f}" if value.is_integer() else str(value)
        else:
            return str(value)