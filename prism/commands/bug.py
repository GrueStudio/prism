"""
Bug command group for the Prism CLI.

Commands for managing bug tracking including creation, lifecycle
management, and log attachment.
"""
import click
from typing import Optional
from prism.managers.bug_manager import BugManager
from prism.utils import to_local_time


@click.group()
def bug():
    """Manage bug tracking.

    Bugs are tracked issues with a defined lifecycle:
    open → reproduced → found → fixed → implemented

    Each bug has a unique ID format: BUGTYPEddmmyy_number
    (e.g., PHYS100326_01 for a physics bug on March 10, 2026)
    """
    pass


@bug.command(name="list")
@click.argument("search", required=False)
@click.option(
    "-s",
    "--status",
    "status_filter",
    help="Status filter (+/- shorthand: o=open, r=reproduced, f=found, x=fixed, i=implemented). e.g. -xor, +f",
)
@click.option(
    "--sort",
    "sort_by",
    default="id",
    type=click.Choice(["id", "status", "created_at", "updated_at"]),
    help="Field to sort by (default: id).",
)
@click.option(
    "--order",
    type=click.Choice(["asc", "desc"]),
    default="asc",
    help="Sort order (default: asc).",
)
def list_bugs(search: Optional[str], status_filter: Optional[str], sort_by: str, order: str):
    """List bugs with filtering and sorting.

    SEARCH is an optional string to filter bugs by ID, description, or root cause.
    Use -s/--status with shorthand to filter by status:
      -xor  -> exclude fixed, open, reproduced (leaves found, implemented)
      +f    -> include only found
    """
    manager = BugManager()
    bugs = manager.list_bugs(
        status_filter=status_filter,
        search=search,
        sort_by=sort_by,
        order=order
    )

    if not bugs:
        click.echo("No bugs found.")
        return

    # Table header
    header = f"{'ID':<15} {'Status':<12} {'Updated':<20} {'Description'}"
    click.secho(header, bold=True, underline=True)

    status_colors = {
        "open": "red",
        "reproduced": "yellow",
        "found": "magenta",
        "fixed": "blue",
        "implemented": "green"
    }

    for bug in bugs:
        # Format updated time
        updated_str = to_local_time(bug.updated_at).strftime("%Y-%m-%d %H:%M:%S")
        
        # Format description (truncate if too long)
        desc = bug.description.replace("\n", " ")
        if len(desc) > 50:
            desc = desc[:47] + "..."
            
        # Color status
        status_color = status_colors.get(bug.status.value, "white")
        
        # Build line
        click.echo(f"{bug.bug_id:<15} ", nl=False)
        click.secho(f"{bug.status.value:<12} ", fg=status_color, nl=False)
        click.echo(f"{updated_str:<20} {desc}")


@bug.command(name="show")
@click.argument("bug_id")
def show_bug(bug_id: str):
    """Show details for a bug.

    BUG_ID is the bug identifier (e.g., PHYS100326_01).
    """
    manager = BugManager()
    bug_item = manager.get_bug(bug_id)
    
    if not bug_item:
        click.secho(f"Error: Bug '{bug_id}' not found.", fg="red")
        return

    click.secho(f"Bug: {bug_item.bug_id}", fg="cyan", bold=True)
    click.echo("-" * (len(bug_item.bug_id) + 5))
    click.echo(f"Type:        {bug_item.bug_type.name} ({bug_item.bug_type.prefix})")
    
    status_colors = {
        "open": "red",
        "reproduced": "yellow",
        "found": "magenta",
        "fixed": "blue",
        "implemented": "green"
    }
    status_color = status_colors.get(bug_item.status.value, "white")
    click.echo("Status:      ", nl=False)
    click.secho(bug_item.status.value, fg=status_color, bold=True)
    
    click.echo(f"Created:     {to_local_time(bug_item.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"Updated:     {to_local_time(bug_item.updated_at).strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"\nDescription: {bug_item.description}")
    
    if bug_item.steps_to_reproduce:
        click.echo(f"\nSteps to Reproduce:\n{bug_item.steps_to_reproduce}")
    
    if bug_item.root_cause:
        click.echo(f"\nRoot Cause:\n{bug_item.root_cause}")
        
    if bug_item.fix_description:
        click.echo(f"\nFix Description:\n{bug_item.fix_description}")

    if bug_item.logs:
        click.echo(f"\nLogs ({len(bug_item.logs)}):")
        for log in bug_item.logs:
            click.echo(f"  - {log.title} ({log.log_type}) [{log.id[:8]}]")


@bug.command(name="add")
@click.option("-t", "--type", "bug_type_name", required=True, help="Bug type name.")
@click.option("-d", "--description", required=True, help="Bug description.")
def add_bug(bug_type_name: str, description: str):
    """Add a new bug."""
    manager = BugManager()
    try:
        bug_item = manager.add_bug(bug_type_name, description)
        click.secho(f"Successfully added bug: {bug_item.bug_id}", fg="green")
    except ValueError as e:
        click.secho(f"Error: {e}", fg="red")


@bug.command(name="update")
@click.argument("bug_id")
@click.argument("description", required=False)
@click.option("-f", "--file", "filepath", type=click.Path(exists=True, dir_okay=False), help="File containing the description.")
def update_bug(bug_id: str, description: Optional[str], filepath: Optional[str]):
    """Progress a bug to its next status in the lifecycle.

    Automatically advances the bug's status (e.g., open -> reproduced).
    The provided description is intelligently assigned to the correct field:
    - open->reproduced: sets 'steps_to_reproduce'
    - reproduced->found: sets 'root_cause'
    - found->fixed: sets 'fix_description'
    """
    if not description and not filepath:
        # For the fixed -> implemented transition, no description is needed.
        # We'll pass an empty string and let the manager handle it.
        desc_content = ""
    elif description and filepath:
        raise click.ClickException("Cannot provide both a description argument and a --file option.")
    elif filepath:
        try:
            with open(filepath, "r") as f:
                desc_content = f.read()
        except Exception as e:
            raise click.ClickException(f"Error reading file '{filepath}': {e}")
    else:
        desc_content = description if description else ""


    manager = BugManager()
    try:
        updated_bug = manager.progress_bug_status(bug_id, desc_content)
        click.secho(f"Successfully updated bug '{bug_id}' to status '{updated_bug.status.value}'.", fg="green")
    except ValueError as e:
        click.secho(f"Error: {e}", fg="red")


@bug.command(name="edit")
@click.argument("bug_id")
@click.option("-d", "--description", help="New description.")
@click.option("-s", "--steps", "steps_to_reproduce", help="Steps to reproduce.")
@click.option("-r", "--root-cause", "root_cause", help="Root cause.")
@click.option("-f", "--fix", "fix_description", help="Fix description.")
def edit_bug(bug_id: str, **kwargs):
    """Edit bug fields (not status, not ID, not type)."""
    manager = BugManager()
    
    # Filter out None values
    updates = {k: v for k, v in kwargs.items() if v is not None}
    
    if not updates:
        click.echo("No fields to update.")
        return
        
    try:
        bug_item = manager.update_bug(bug_id, **updates)
        click.secho(f"Successfully updated bug: {bug_item.bug_id}", fg="green")
    except ValueError as e:
        click.secho(f"Error: {e}", fg="red")


@bug.command(name="delete")
@click.argument("bug_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation.")
def delete_bug(bug_id: str, yes: bool):
    """Delete a bug."""
    if not yes:
        if not click.confirm(f"Are you sure you want to delete bug '{bug_id}'?"):
            return

    manager = BugManager()
    if manager.delete_bug(bug_id):
        click.secho(f"Successfully deleted bug: {bug_id}", fg="green")
    else:
        click.secho(f"Error: Bug '{bug_id}' not found.", fg="red")


# Log subcommand group
@bug.group()
def log():
    """Manage bug logs."""
    pass


@log.command(name="add")
@click.argument("bug_id")
@click.option("--title", required=True, help="Log title.")
@click.option("--type", "log_type", default="general", help="Log type.")
def add_log(bug_id: str, title: str, log_type: str):
    """Add a log to a bug."""
    click.echo(f"Bug log add command - coming soon (bug: {bug_id})")


@log.command(name="list")
@click.argument("bug_id")
def list_logs(bug_id: str):
    """List logs for a bug."""
    click.echo(f"Bug log list command - coming soon (bug: {bug_id})")


@log.command(name="show")
@click.argument("bug_id")
@click.argument("log_id")
def show_log(bug_id: str, log_id: str):
    """Show log content."""
    click.echo(f"Bug log show command - coming soon (bug: {bug_id}, log: {log_id})")


@log.command(name="delete")
@click.argument("bug_id")
@click.argument("log_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation.")
def delete_log(bug_id: str, log_id: str, yes: bool):
    """Delete a log from a bug."""
    click.echo(f"Bug log delete command - coming soon (bug: {bug_id}, log: {log_id})")
