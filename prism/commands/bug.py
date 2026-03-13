"""
Bug command group for the Prism CLI.

Commands for managing bug tracking including creation, lifecycle
management, and log attachment.
"""
import click


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
    click.echo(f"Bug show command - coming soon (bug: {bug_id})")


@bug.command(name="add")
@click.option("-t", "--type", "bug_type_name", required=True, help="Bug type name.")
@click.option("-d", "--description", required=True, help="Bug description.")
def add_bug(bug_type_name: str, description: str):
    """Add a new bug."""
    click.echo(f"Bug add command - coming soon (type: {bug_type_name})")


@bug.command(name="update")
@click.argument("bug_id")
@click.option("--to", "to_status", required=True, help="Target status.")
@click.option("--description", required=True, help="Description of the transition.")
def update_bug(bug_id: str, to_status: str, description: str):
    """Update bug status (progress through lifecycle)."""
    click.echo(f"Bug update command - coming soon (bug: {bug_id}, to: {to_status})")


@bug.command(name="edit")
@click.argument("bug_id")
def edit_bug(bug_id: str):
    """Edit bug fields (not status, not ID, not type)."""
    click.echo(f"Bug edit command - coming soon (bug: {bug_id})")


@bug.command(name="delete")
@click.argument("bug_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation.")
def delete_bug(bug_id: str, yes: bool):
    """Delete a bug."""
    click.echo(f"Bug delete command - coming soon (bug: {bug_id})")


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
