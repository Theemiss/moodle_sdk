"""Course category management CLI commands."""

import asyncio
import json
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich import box
from rich.prompt import Confirm

from client.moodle_client import AsyncMoodleClient
from services.category_service import CategoryService
from schemas.category import CategoryCreate, CategoryUpdate
from cli.output import print_error, print_success, print_warning, print_json_data

app = typer.Typer(help="Course category management commands")
console = Console()


@app.command("list")
def list_categories(
    parent_id: Optional[int] = typer.Option(None, "--parent", "-p", help="Filter by parent category ID"),
    include_hidden: bool = typer.Option(False, "--include-hidden", help="Include hidden categories"),
    format: str = typer.Option("table", "--format", help="Output format (table, json, tree)"),
) -> None:
    """List all course categories."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            categories = await service.list_categories(parent_id=parent_id, include_hidden=include_hidden)
            
            if format == "json":
                data = [c.model_dump() for c in categories]
                print_json_data(data)
            elif format == "tree":
                # Show as tree if no parent filter
                if parent_id is None:
                    trees = await service.get_category_tree()
                    for tree_root in trees:
                        _display_category_tree(tree_root)
                else:
                    # Show flat list
                    _display_categories_table(categories)
            else:
                _display_categories_table(categories)
    
    asyncio.run(_run())


@app.command("get")
def get_category(
    category_id: int = typer.Argument(..., help="Category ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Get category details by ID."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            try:
                category = await service.get_category(category_id)
                
                if format == "json":
                    print_json_data(category.model_dump())
                else:
                    # Get subcategories count
                    subcats = await service.list_categories(parent_id=category_id)
                    
                    # Get courses count
                    courses = await service.get_category_courses(category_id)
                    
                    info = f"""
[bold cyan]ID:[/] {category.id}
[bold green]Name:[/] {category.name}
[bold]ID Number:[/] {category.idnumber or 'N/A'}
[bold]Parent:[/] {category.parent} ({'Top-level' if category.parent == 0 else ''})
[bold]Path:[/] {category.path}
[bold]Depth:[/] {category.depth}
[bold]Visible:[/] {'Yes' if category.visible else 'No'}
[bold]Sort Order:[/] {category.sortorder}

[bold]Statistics:[/]
  • Courses: {category.coursecount} (direct)
  • Subcategories: {len(subcats)}
  • Total Courses (including subs): {sum(c.coursecount for c in subcats) + category.coursecount}

[bold]Description:[/]
{category.description or 'No description'}
"""
                    console.print(Panel(info, title=f"Category {category_id}", border_style="blue"))
                    
            except Exception as e:
                print_error(f"Failed to get category: {e}")
    
    asyncio.run(_run())


@app.command("create")
def create_category(
    name: str = typer.Option(..., "--name", "-n", help="Category name"),
    parent: int = typer.Option(0, "--parent", "-p", help="Parent category ID"),
    idnumber: Optional[str] = typer.Option(None, "--idnumber", help="Category ID number"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Category description"),
    theme: Optional[str] = typer.Option(None, "--theme", help="Category theme"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created without executing"),
) -> None:
    """Create a new course category."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would create category:[/]")
            console.print(f"  Name: {name}")
            console.print(f"  Parent: {parent}")
            console.print(f"  ID Number: {idnumber or 'None'}")
            return
        
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            try:
                category_data = CategoryCreate(
                    name=name,
                    parent=parent,
                    idnumber=idnumber,
                    description=description,
                    theme=theme,
                )
                category = await service.create_category(category_data)
                print_success(f"Category created successfully with ID: {category.id}")
                
                # Show category details
                console.print(f"Name: {category.name}")
                console.print(f"Parent: {category.parent}")
                
            except Exception as e:
                print_error(f"Failed to create category: {e}")
    
    asyncio.run(_run())


@app.command("update")
def update_category(
    category_id: int = typer.Argument(..., help="Category ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New category name"),
    parent: Optional[int] = typer.Option(None, "--parent", "-p", help="New parent category ID"),
    idnumber: Optional[str] = typer.Option(None, "--idnumber", help="New ID number"),
    visible: Optional[bool] = typer.Option(None, "--visible/--hidden", help="Set visibility"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    theme: Optional[str] = typer.Option(None, "--theme", help="New theme"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be updated without executing"),
) -> None:
    """Update an existing category."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would update category {category_id}:[/]")
            changes = []
            if name: changes.append(f"Name: {name}")
            if parent is not None: changes.append(f"Parent: {parent}")
            if idnumber: changes.append(f"ID Number: {idnumber}")
            if visible is not None: changes.append(f"Visible: {visible}")
            if description: changes.append("Description: (updated)")
            if theme: changes.append(f"Theme: {theme}")
            
            if changes:
                for change in changes:
                    console.print(f"  • {change}")
            else:
                console.print("  No changes specified")
            return
        
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            try:
                update_data = {}
                if name is not None:
                    update_data["name"] = name
                if parent is not None:
                    update_data["parent"] = parent
                if idnumber is not None:
                    update_data["idnumber"] = idnumber
                if visible is not None:
                    update_data["visible"] = 1 if visible else 0
                if description is not None:
                    update_data["description"] = description
                if theme is not None:
                    update_data["theme"] = theme
                
                category_update = CategoryUpdate(**update_data)
                category = await service.update_category(category_id, category_update)
                print_success(f"Category {category_id} updated successfully")
                
            except Exception as e:
                print_error(f"Failed to update category: {e}")
    
    asyncio.run(_run())


@app.command("delete")
def delete_category(
    category_id: int = typer.Argument(..., help="Category ID to delete"),
    new_parent: Optional[int] = typer.Option(None, "--new-parent", help="Move subcategories to this parent"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Delete all subcategories and courses"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without executing"),
) -> None:
    """Delete a category."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            
            # Get category info for confirmation
            try:
                category = await service.get_category(category_id)
            except:
                print_error(f"Category {category_id} not found")
                return
            
            # Check for subcategories
            subcats = await service.list_categories(parent_id=category_id)
            courses = await service.get_category_courses(category_id)
            
            if dry_run:
                console.print(f"[yellow]DRY RUN: Would delete category {category_id}:[/]")
                console.print(f"  Name: {category.name}")
                console.print(f"  Subcategories: {len(subcats)}")
                console.print(f"  Direct courses: {len(courses)}")
                if subcats and not recursive and not new_parent:
                    console.print(f"  ⚠️  Subcategories will be orphaned!")
                return
            
            # Confirm deletion
            if not force:
                console.print(f"[red]Warning: About to delete category '{category.name}' (ID: {category_id})[/]")
                console.print(f"  • Subcategories: {len(subcats)}")
                console.print(f"  • Direct courses: {len(courses)}")
                
                if subcats and not recursive and not new_parent:
                    console.print("[red]⚠️  This category has subcategories but you haven't specified --recursive or --new-parent[/]")
                    console.print("  Subcategories will become top-level categories")
                
                if not Confirm.ask("Are you sure you want to continue?"):
                    console.print("[yellow]Cancelled[/]")
                    return
            
            try:
                success = await service.delete_category(
                    category_id, 
                    new_parent_id=new_parent,
                    recursive=recursive
                )
                if success:
                    print_success(f"Category {category_id} deleted successfully")
                else:
                    print_error(f"Failed to delete category {category_id}")
            except ValueError as e:
                print_error(str(e))
            except Exception as e:
                print_error(f"Failed to delete category: {e}")
    
    asyncio.run(_run())


@app.command("move")
def move_category(
    category_id: int = typer.Argument(..., help="Category ID to move"),
    new_parent: int = typer.Argument(..., help="New parent category ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Move a category to a new parent."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would move category {category_id} to parent {new_parent}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            try:
                category = await service.move_category(category_id, new_parent)
                print_success(f"Category {category_id} moved successfully")
                console.print(f"New parent: {category.parent}")
            except Exception as e:
                print_error(f"Failed to move category: {e}")
    
    asyncio.run(_run())


@app.command("tree")
def category_tree(
    root_id: Optional[int] = typer.Option(None, "--root", "-r", help="Root category ID"),
    format: str = typer.Option("tree", "--format", help="Output format (tree, json)"),
) -> None:
    """Show hierarchical category tree."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            trees = await service.get_category_tree(root_id=root_id)
            
            if format == "json":
                data = [t.model_dump() for t in trees]
                print_json_data(data)
            else:
                if not trees:
                    console.print("[yellow]No categories found[/]")
                    return
                
                for tree_root in trees:
                    _display_category_tree(tree_root)
    
    asyncio.run(_run())


@app.command("permissions")
def category_permissions(
    category_id: int = typer.Argument(..., help="Category ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """Show role permissions for a category."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            permissions = await service.get_category_permissions(category_id)
            
            if format == "json":
                data = [p.model_dump() for p in permissions]
                print_json_data(data)
            else:
                if not permissions:
                    console.print(f"[yellow]No role assignments found for category {category_id}[/]")
                    return
                
                table = Table(title=f"Category {category_id} - Role Permissions", box=box.ROUNDED)
                table.add_column("Role ID", style="cyan")
                table.add_column("Role Name")
                table.add_column("User ID", justify="right")
                table.add_column("Permission")
                
                for perm in permissions:
                    table.add_row(
                        str(perm.role_id),
                        perm.role_name,
                        str(perm.user_id),
                        perm.permission,
                    )
                
                console.print(table)
    
    asyncio.run(_run())


@app.command("assign-role")
def assign_role(
    category_id: int = typer.Argument(..., help="Category ID"),
    user_id: int = typer.Argument(..., help="User ID"),
    role_id: int = typer.Argument(..., help="Role ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Assign a role to a user in a category context."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would assign role {role_id} to user {user_id} in category {category_id}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            try:
                success = await service.assign_role(category_id, user_id, role_id)
                if success:
                    print_success(f"Role {role_id} assigned to user {user_id} in category {category_id}")
                else:
                    print_error("Failed to assign role")
            except Exception as e:
                print_error(f"Failed to assign role: {e}")
    
    asyncio.run(_run())


@app.command("unassign-role")
def unassign_role(
    category_id: int = typer.Argument(..., help="Category ID"),
    user_id: int = typer.Argument(..., help="User ID"),
    role_id: int = typer.Argument(..., help="Role ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Unassign a role from a user in a category context."""
    async def _run():
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would unassign role {role_id} from user {user_id} in category {category_id}[/]")
            return
        
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            try:
                success = await service.unassign_role(category_id, user_id, role_id)
                if success:
                    print_success(f"Role {role_id} unassigned from user {user_id} in category {category_id}")
                else:
                    print_error("Failed to unassign role")
            except Exception as e:
                print_error(f"Failed to unassign role: {e}")
    
    asyncio.run(_run())


@app.command("courses")
def category_courses(
    category_id: int = typer.Argument(..., help="Category ID"),
    format: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List all courses in a category."""
    async def _run():
        async with AsyncMoodleClient() as client:
            service = CategoryService(client)
            courses = await service.get_category_courses(category_id)
            
            if format == "json":
                print_json_data(courses)
            else:
                if not courses:
                    console.print(f"[yellow]No courses found in category {category_id}[/]")
                    return
                
                table = Table(title=f"Category {category_id} - Courses", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Short Name")
                table.add_column("Full Name")
                table.add_column("Visible", justify="center")
                
                for course in courses:
                    visible = "✓" if course.get("visible", 1) else "✗"
                    table.add_row(
                        str(course.get("id")),
                        course.get("shortname", ""),
                        course.get("fullname", "")[:50],
                        visible,
                    )
                
                console.print(table)
    
    asyncio.run(_run())


def _display_categories_table(categories):
    """Display categories in a table."""
    if not categories:
        console.print("[yellow]No categories found[/]")
        return
    
    table = Table(title=f"Categories (Total: {len(categories)})", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Parent", justify="right")
    table.add_column("Courses", justify="right")
    table.add_column("Depth", justify="right")
    table.add_column("Visible", justify="center")
    
    for cat in categories:
        visible = "✓" if cat.visible else "✗"
        visible_style = "green" if cat.visible else "red"
        
        table.add_row(
            str(cat.id),
            cat.name,
            str(cat.parent) if cat.parent != 0 else "Top",
            str(cat.coursecount),
            str(cat.depth),
            f"[{visible_style}]{visible}[/]",
        )
    
    console.print(table)


def _display_category_tree(node, tree=None, prefix=""):
    """Recursively display category tree."""
    if tree is None:
        tree = Tree(f"[bold blue]Category Tree[/]")
        tree.add(f"[cyan]ID: {node.id}[/] - [green]{node.name}[/] [dim]({node.coursecount} courses)[/]")
        _tree = tree
    else:
        branch = tree.add(f"[cyan]ID: {node.id}[/] - [green]{node.name}[/] [dim]({node.coursecount} courses)[/]")
        _tree = branch
    
    for child in node.children:
        _display_category_tree(child, _tree)
    
    if prefix == "":
        console.print(tree)