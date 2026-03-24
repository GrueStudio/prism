"""
Bug command group for the Prism CLI.

Commands for managing bug tracking including creation, lifecycle
management, and log attachment.
"""
import click
from prism.managers.bug_manager import BugManager


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
def list_bugs():
    """List all bugs."""
    click.echo("Bug list command - coming soon")


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
    
    click.echo(f"Created:     {bug_item.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"Updated:     {bug_item.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
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
@click.option("--to", "to_status", required=True, help="Target status.")
@click.option("--description", required=True, help="Description of the transition.")
def update_bug(bug_id: str, to_status: str, description: str):
    """Update bug status (progress through lifecycle)."""
    click.echo(f"Bug update command - coming soon (bug: {bug_id}, to: {to_status})")


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
