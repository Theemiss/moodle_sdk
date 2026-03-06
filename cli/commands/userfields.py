"""User custom fields management CLI commands."""

import asyncio
import json
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.prompt import Confirm, Prompt

from client.moodle_client import AsyncMoodleClient
from services.userfield_service import UserFieldService
from schemas.userfield import (
    UserFieldCreate, 
    UserFieldUpdate, 
    UserFieldDatatype
)
from cli.output import print_error, print_success, print_warning, print_json_data

app = typer.Typer(help="User custom fields management commands")
console = Console()



@app.command("list")
def list_fields(
    category_id: Optional[int] = typer.Option(None, "--category", "-c", help="Filter by category ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List all user custom fields."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            fields = await service.list_fields(category_id=category_id)
            
            if format == "json":
                data = [f.model_dump() for f in fields]
                print_json_data(data)
            else:
                if not fields:
                    console.print("[yellow]No user custom fields found[/]")
                    console.print("\n[dim]Note: User custom fields feature may not be enabled in this Moodle instance.[/]")
                    console.print("[dim]To enable it, an administrator needs to:[/]")
                    console.print("[dim]  1. Go to Site administration → Users → Accounts → User profile fields[/]")
                    console.print("[dim]  2. Add custom fields as needed[/]")
                    return
                
                table = Table(title="User Custom Fields", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Short Name")
                table.add_column("Name")
                table.add_column("Type")
                table.add_column("Category")
                table.add_column("Required", justify="center")
                table.add_column("Visible", justify="center")
                
                for field in fields:
                    required = "✓" if field.required else "✗"
                    visible = "✓" if field.visible == 2 else "✗"
                    
                    table.add_row(
                        str(field.id),
                        field.shortname,
                        field.name,
                        field.datatype,
                        str(field.categoryid),
                        required,
                        visible,
                    )
                
                console.print(table)
    
    asyncio.run(_run())



@app.command("get")
def get_field(
    field_id: int = typer.Argument(..., help="Field ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get user custom field details by ID."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            try:
                field = await service.get_field(field_id)
                
                if format == "json":
                    print_json_data(field.model_dump())
                else:
                    info = f"""
[bold cyan]ID:[/] {field.id}
[bold green]Short Name:[/] {field.shortname}
[bold]Name:[/] {field.name}
[bold]Type:[/] {field.datatype}
[bold]Category ID:[/] {field.categoryid}
[bold]Sort Order:[/] {field.sortorder}

[bold]Settings:[/]
  • Required: {'Yes' if field.required else 'No'}
  • Locked: {'Yes' if field.locked else 'No'}
  • Visible: {'Yes' if field.visible == 2 else 'No'}
  • Force Unique: {'Yes' if field.forceunique else 'No'}
  • Show on Signup: {'Yes' if field.signup else 'No'}

[bold]Default Value:[/] {field.defaultdata or 'None'}

[bold]Description:[/]
{field.description or 'No description'}
"""
                    if field.param1 and field.datatype in ["menu", "select", "radio"]:
                        options = field.param1 if isinstance(field.param1, list) else str(field.param1).split('\n')
                        info += f"\n[bold]Options:[/]\n"
                        for i, opt in enumerate(options, 1):
                            if opt.strip():
                                info += f"  {i}. {opt}\n"
                    
                    console.print(Panel(info, title=f"User Field {field_id}", border_style="blue"))
                    
            except Exception as e:
                print_error(f"Failed to get field: {e}")
    
    asyncio.run(_run())


@app.command("create")
def create_field(
    shortname: str = typer.Option(..., "--shortname", "-s", help="Field shortname (unique identifier)"),
    name: str = typer.Option(..., "--name", "-n", help="Field display name"),
    datatype: UserFieldDatatype = typer.Option(..., "--type", "-t", help="Field data type"),
    category_id: int = typer.Option(0, "--category", "-c", help="Category ID"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Field description"),
    required: bool = typer.Option(False, "--required", help="Field is required"),
    locked: bool = typer.Option(False, "--locked", help="Field is locked"),
    visible: bool = typer.Option(True, "--visible/--hidden", help="Field visibility"),
    unique: bool = typer.Option(False, "--unique", help="Force unique values"),
    signup: bool = typer.Option(False, "--signup", help="Show on signup page"),
    default: Optional[str] = typer.Option(None, "--default", help="Default value"),
    options: Optional[List[str]] = typer.Option(None, "--option", "-o", help="Options for menu/select fields (can be used multiple times)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created without executing"),
) -> None:
    """Create a new user custom field."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would create user field:[/]")
            console.print(f"  Short Name: {shortname}")
            console.print(f"  Name: {name}")
            console.print(f"  Type: {datatype.value}")
            console.print(f"  Category: {category_id}")
            if options:
                console.print(f"  Options: {', '.join(options)}")
            return
        
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            try:
                field_data = UserFieldCreate(
                    shortname=shortname,
                    name=name,
                    datatype=datatype,
                    categoryid=category_id,
                    description=description,
                    required=required,
                    locked=locked,
                    visible=visible,
                    forceunique=unique,
                    signup=signup,
                    defaultdata=default,
                    options=options,
                )
                field = await service.create_field(field_data)
                print_success(f"User field created successfully with ID: {field.id}")
                
            except Exception as e:
                print_error(f"Failed to create field: {e}")
    
    asyncio.run(_run())


@app.command("update")
def update_field(
    field_id: int = typer.Argument(..., help="Field ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New display name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    required: Optional[bool] = typer.Option(None, "--required/--not-required", help="Field required"),
    locked: Optional[bool] = typer.Option(None, "--locked/--unlocked", help="Field locked"),
    visible: Optional[bool] = typer.Option(None, "--visible/--hidden", help="Field visibility"),
    unique: Optional[bool] = typer.Option(None, "--unique/--not-unique", help="Force unique values"),
    signup: Optional[bool] = typer.Option(None, "--signup/--no-signup", help="Show on signup page"),
    default: Optional[str] = typer.Option(None, "--default", help="Default value"),
    category_id: Optional[int] = typer.Option(None, "--category", "-c", help="New category ID"),
    options: Optional[List[str]] = typer.Option(None, "--option", "-o", help="Options for menu/select fields"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be updated without executing"),
) -> None:
    """Update an existing user custom field."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would update field {field_id}:[/]")
            changes = []
            if name: changes.append(f"Name: {name}")
            if description: changes.append("Description: (updated)")
            if required is not None: changes.append(f"Required: {required}")
            if locked is not None: changes.append(f"Locked: {locked}")
            if visible is not None: changes.append(f"Visible: {visible}")
            if unique is not None: changes.append(f"Unique: {unique}")
            if signup is not None: changes.append(f"Signup: {signup}")
            if default: changes.append(f"Default: {default}")
            if category_id: changes.append(f"Category: {category_id}")
            if options: changes.append(f"Options: {len(options)} options")
            
            if changes:
                for change in changes:
                    console.print(f"  • {change}")
            else:
                console.print("  No changes specified")
            return
        
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            try:
                update_data = {}
                if name is not None:
                    update_data["name"] = name
                if description is not None:
                    update_data["description"] = description
                if required is not None:
                    update_data["required"] = required
                if locked is not None:
                    update_data["locked"] = locked
                if visible is not None:
                    update_data["visible"] = visible
                if unique is not None:
                    update_data["forceunique"] = unique
                if signup is not None:
                    update_data["signup"] = signup
                if default is not None:
                    update_data["defaultdata"] = default
                if category_id is not None:
                    update_data["categoryid"] = category_id
                if options is not None:
                    update_data["options"] = options
                
                field_update = UserFieldUpdate(**update_data)
                field = await service.update_field(field_id, field_update)
                print_success(f"Field {field_id} updated successfully")
                
            except Exception as e:
                print_error(f"Failed to update field: {e}")
    
    asyncio.run(_run())


@app.command("delete")
def delete_field(
    field_id: int = typer.Argument(..., help="Field ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without executing"),
) -> None:
    """Delete a user custom field."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            
            # Get field info for confirmation
            try:
                field = await service.get_field(field_id)
            except:
                print_error(f"Field {field_id} not found")
                return
            
            if dry_run:
                console.print(f"[yellow]DRY RUN: Would delete field {field_id}:[/]")
                console.print(f"  Name: {field.name}")
                console.print(f"  Short Name: {field.shortname}")
                console.print(f"  Type: {field.datatype}")
                return
            
            # Confirm deletion
            if not force:
                console.print(f"[red]Warning: About to delete user field '{field.name}' (ID: {field_id})[/]")
                console.print(f"  Type: {field.datatype}")
                console.print(f"  This will remove all data for this field from all user profiles")
                
                if not Confirm.ask("Are you sure you want to continue?"):
                    console.print("[yellow]Cancelled[/]")
                    return
            
            try:
                success = await service.delete_field(field_id)
                if success:
                    print_success(f"Field {field_id} deleted successfully")
                else:
                    print_error(f"Failed to delete field {field_id}")
            except Exception as e:
                print_error(f"Failed to delete field: {e}")
    
    asyncio.run(_run())



@app.command("categories")
def list_categories(
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List user field categories."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            categories = await service.list_categories()
            
            if format == "json":
                data = [c.model_dump() for c in categories]
                print_json_data(data)
            else:
                if not categories:
                    console.print("[yellow]No user field categories found[/]")
                    console.print("\n[dim]Note: User custom fields feature may not be enabled in this Moodle instance.[/]")
                    console.print("[dim]Categories are created automatically when you add custom fields.[/]")
                    return
                
                table = Table(title="User Field Categories", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Name")
                table.add_column("Sort Order", justify="right")
                
                # Get fields count for each category
                fields = await service.list_fields()
                fields_by_category = {}
                for field in fields:
                    cat_id = field.categoryid
                    if cat_id not in fields_by_category:
                        fields_by_category[cat_id] = 0
                    fields_by_category[cat_id] += 1
                
                for cat in categories:
                    field_count = fields_by_category.get(cat.id, 0)
                    table.add_row(
                        str(cat.id),
                        f"{cat.name} [dim]({field_count} fields)[/]",
                        str(cat.sortorder),
                    )
                
                console.print(table)
    
    asyncio.run(_run())

@app.command("create-category")
def create_category(
    name: str = typer.Option(..., "--name", "-n", help="Category name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created without executing"),
) -> None:
    """Create a new user field category."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would create category: {name}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            try:
                category = await service.create_category(name)
                print_success(f"Category created successfully with ID: {category.id}")
            except Exception as e:
                print_error(f"Failed to create category: {e}")
    
    asyncio.run(_run())


@app.command("delete-category")
def delete_category(
    category_id: int = typer.Argument(..., help="Category ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without executing"),
) -> None:
    """Delete a user field category."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            
            # Check if category has fields
            fields = await service.list_fields(category_id=category_id)
            
            if dry_run:
                console.print(f"[yellow]DRY RUN: Would delete category {category_id}[/]")
                console.print(f"  Fields in category: {len(fields)}")
                return
            
            if fields and not force:
                console.print(f"[red]Warning: Category {category_id} has {len(fields)} fields[/]")
                console.print("  Deleting the category will not delete the fields, but they will be uncategorized")
                if not Confirm.ask("Are you sure you want to continue?"):
                    console.print("[yellow]Cancelled[/]")
                    return
            
            try:
                success = await service.delete_category(category_id)
                if success:
                    print_success(f"Category {category_id} deleted successfully")
                else:
                    print_error(f"Failed to delete category {category_id}")
            except Exception as e:
                print_error(f"Failed to delete category: {e}")
    
    asyncio.run(_run())


@app.command("user-values")
def user_field_values(
    user_id: int = typer.Argument(..., help="User ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get custom field values for a user."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            values = await service.get_user_field_values(user_id)
            
            if format == "json":
                data = [v.model_dump() for v in values]
                print_json_data(data)
            else:
                if not values:
                    console.print(f"[yellow]No custom field values found for user {user_id}[/]")
                    return
                
                table = Table(title=f"User {user_id} - Custom Field Values", box=box.ROUNDED)
                table.add_column("Field", style="cyan")
                table.add_column("Value")
                
                for val in values:
                    table.add_row(val.field_name, str(val.value) if val.value else "[dim]empty[/]")
                
                console.print(table)
    
    asyncio.run(_run())


@app.command("set-value")
def set_field_value(
    user_id: int = typer.Argument(..., help="User ID"),
    field_name: str = typer.Argument(..., help="Field shortname"),
    value: str = typer.Argument(..., help="Value to set"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Set a custom field value for a user."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would set {field_name} = '{value}' for user {user_id}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            try:
                success = await service.set_user_field_value(user_id, field_name, value)
                if success:
                    print_success(f"Field '{field_name}' updated for user {user_id}")
                else:
                    print_error("Failed to set field value")
            except Exception as e:
                print_error(f"Failed to set value: {e}")
    
    asyncio.run(_run())


@app.command("stats")
def field_stats(
    field_id: int = typer.Argument(..., help="Field ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get statistics for a custom field."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = UserFieldService(client)
            stats = await service.get_field_stats(field_id)
            
            if format == "json":
                print_json_data(stats)
            else:
                if "error" in stats:
                    print_error(f"Failed to get stats: {stats['error']}")
                    return
                
                console.print(Panel(
                    f"[bold cyan]Field:[/] {stats['field_name']} ({stats['field_shortname']})\n"
                    f"[bold]Type:[/] {stats['datatype']}\n"
                    f"[bold]Users with value:[/] {stats['users_with_value']}\n",
                    title=f"Field {field_id} Statistics",
                    border_style="green",
                ))
                
                if stats.get('value_distribution'):
                    dist_table = Table(title="Value Distribution", box=box.ROUNDED)
                    dist_table.add_column("Value", style="cyan")
                    dist_table.add_column("Count", justify="right")
                    
                    for value, count in stats['value_distribution'].items():
                        dist_table.add_row(value, str(count))
                    
                    console.print(dist_table)
    
    asyncio.run(_run())