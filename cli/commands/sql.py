"""SQL query command for moodlectl."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from client.query_engine import QueryEngine, AsyncQueryEngine
from client.query_parser import OutputFormat

app = typer.Typer(help="Execute SQL queries against the database")
console = Console()


@app.command("query")
def execute_query(
    query: str = typer.Argument(..., help="SQL query to execute"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help="JSON string of query parameters"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: json, csv, table, compact, raw"),
    allow_write: bool = typer.Option(False, "--allow-write", "-w", help="Allow write operations in safe mode"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Maximum number of rows to return"),
    json_params: bool = typer.Option(False, "--json-params", "-j", help="Parse parameters as JSON"),
):
    """Execute a raw SQL query against the database."""
    try:
        # Parse parameters if provided
        params_dict = None
        if params:
            if json_params or params.startswith(("{", "[")):
                import json
                params_dict = json.loads(params)
            else:
                # Simple key=value format
                params_dict = {}
                for pair in params.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params_dict[key.strip()] = value.strip()
        
        # Create query engine
        engine = QueryEngine()
        
        # Execute query
        with console.status("[bold green]Executing query..."):
            result, row_count = engine.execute(
                query=query,
                params=params_dict,
                output_format=format,
                allow_write=allow_write,
                max_rows=limit,
            )
        
        # Display results
        if isinstance(result, str):
            console.print(result)
        else:
            console.print(result)
        
        if row_count is not None:
            console.print(f"\n[dim]Rows returned: {row_count}[/dim]")
        
        engine.close()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("tables")
def list_tables(
    schema: Optional[str] = typer.Option(None, "--schema", "-s", help="Database schema"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """List all tables in the database."""
    try:
        engine = QueryEngine()
        
        # Query to get all tables
        schema_filter = f"AND table_schema = '{schema}'" if schema else ""
        query = f"""
            SELECT 
                table_schema,
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            {schema_filter}
            ORDER BY table_schema, table_name
        """
        
        result, row_count = engine.execute(
            query=query,
            output_format=format,
            allow_write=False,
        )
        
        if isinstance(result, str):
            console.print(result)
        else:
            console.print(result)
        
        console.print(f"\n[dim]Total tables: {row_count}[/dim]")
        
        engine.close()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("describe")
def describe_table(
    table_name: str = typer.Argument(..., help="Table name"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """Describe table schema."""
    try:
        engine = QueryEngine()
        
        result = engine.get_table_info(table_name)
        
        if isinstance(result, str):
            console.print(result)
        else:
            console.print(result)
        
        engine.close()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("select")
def select_from_table(
    table_name: str = typer.Argument(..., help="Table name"),
    columns: Optional[str] = typer.Option(None, "--columns", "-c", help="Comma-separated list of columns"),
    where: Optional[str] = typer.Option(None, "--where", "-w", help="WHERE clause"),
    order_by: Optional[str] = typer.Option(None, "--order-by", "-o", help="ORDER BY clause"),
    limit: Optional[int] = typer.Option(100, "--limit", "-l", help="Maximum rows"),
    offset: Optional[int] = typer.Option(0, "--offset", help="Offset for pagination"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """Select data from a table with options."""
    try:
        engine = QueryEngine()
        
        # Parse columns
        col_list = columns.split(",") if columns else None
        if col_list:
            col_list = [c.strip() for c in col_list]
        
        result, row_count = engine.query_table(
            table_name=table_name,
            columns=col_list,
            where=where,
            order_by=order_by,
            limit=limit,
            offset=offset,
            output_format=format,
        )
        
        if isinstance(result, str):
            console.print(result)
        else:
            console.print(result)
        
        if row_count is not None:
            console.print(f"\n[dim]Rows returned: {row_count} (limit: {limit})[/dim]")
        
        engine.close()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("insert")
def insert_data(
    table_name: str = typer.Argument(..., help="Table name"),
    data: str = typer.Argument(..., help="JSON data to insert"),
    format: str = typer.Option("json", "--format", "-f", help="Output format"),
    batch: bool = typer.Option(False, "--batch", "-b", help="Treat data as batch array"),
):
    """Insert data into a table."""
    try:
        import json
        
        # Parse JSON data
        parsed_data = json.loads(data)
        
        # Confirm if this is a write operation
        if not Confirm.ask(f"Insert data into {table_name}?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        engine = QueryEngine()
        
        with console.status("[bold green]Inserting data..."):
            result = engine.insert(
                table_name=table_name,
                data=parsed_data,
                output_format=format,
            )
        
        console.print(result)
        engine.close()
        
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Invalid JSON:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("update")
def update_data(
    table_name: str = typer.Argument(..., help="Table name"),
    data: str = typer.Argument(..., help="JSON data to update"),
    where: str = typer.Argument(..., help="WHERE clause"),
    format: str = typer.Option("json", "--format", "-f", help="Output format"),
):
    """Update data in a table."""
    try:
        import json
        
        # Parse JSON data
        parsed_data = json.loads(data)
        
        # Confirm if this is a write operation
        if not Confirm.ask(f"Update data in {table_name}?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        engine = QueryEngine()
        
        with console.status("[bold green]Updating data..."):
            result = engine.update(
                table_name=table_name,
                data=parsed_data,
                where=where,
                output_format=format,
            )
        
        console.print(result)
        engine.close()
        
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Invalid JSON:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("delete")
def delete_data(
    table_name: str = typer.Argument(..., help="Table name"),
    where: str = typer.Argument(..., help="WHERE clause"),
    format: str = typer.Option("json", "--format", "-f", help="Output format"),
):
    """Delete data from a table."""
    try:
        # Confirm if this is a destructive operation
        if not Confirm.ask(f"[bold red]DANGER:[/bold red] Delete from {table_name} where {where}?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        engine = QueryEngine()
        
        with console.status("[bold red]Deleting data..."):
            result = engine.delete(
                table_name=table_name,
                where=where,
                output_format=format,
            )
        
        console.print(result)
        engine.close()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("import-csv")
def import_csv(
    table_name: str = typer.Argument(..., help="Table name"),
    file_path: str = typer.Argument(..., help="CSV file path"),
    delimiter: str = typer.Option(",", "--delimiter", "-d", help="CSV delimiter"),
    has_header: bool = typer.Option(True, "--header/--no-header", help="CSV has header row"),
    format: str = typer.Option("json", "--format", "-f", help="Output format"),
):
    """Import CSV file into a table."""
    try:
        import csv
        
        # Read CSV file
        with open(file_path, 'r') as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
        
        if not rows:
            console.print("[yellow]CSV file is empty[/yellow]")
            return
        
        # Parse data
        if has_header:
            headers = rows[0]
            data_rows = rows[1:]
            data = [dict(zip(headers, row)) for row in data_rows]
        else:
            # Generate column names
            headers = [f"col_{i+1}" for i in range(len(rows[0]))]
            data = [dict(zip(headers, row)) for row in rows]
        
        # Confirm import
        console.print(f"Preview of first 3 records:")
        for i, record in enumerate(data[:3]):
            console.print(f"  {i+1}. {record}")
        
        if len(data) > 3:
            console.print(f"  ... and {len(data) - 3} more records")
        
        if not Confirm.ask(f"Import {len(data)} records into {table_name}?"):
            console.print("[yellow]Import cancelled[/yellow]")
            return
        
        engine = QueryEngine()
        
        with console.status(f"[bold green]Importing {len(data)} records..."):
            result = engine.insert(
                table_name=table_name,
                data=data,
                output_format=format,
            )
        
        console.print(result)
        engine.close()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("async-query")
def async_query_example(
    query: str = typer.Argument(..., help="SQL query to execute"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """Example of async query execution."""
    async def run_async():
        engine = AsyncQueryEngine()
        await engine.initialize()
        
        try:
            result, row_count = await engine.execute(
                query=query,
                output_format=format,
                allow_write=False,
            )
            
            if isinstance(result, str):
                console.print(result)
            else:
                console.print(result)
            
            if row_count is not None:
                console.print(f"\n[dim]Rows returned: {row_count}[/dim]")
                
        finally:
            await engine.close()
    
    try:
        asyncio.run(run_async())
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()