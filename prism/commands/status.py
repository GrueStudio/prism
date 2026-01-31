import click
from prism.tracker import Tracker
from datetime import datetime


@click.command(name='status')
def status():
    """Displays a summary of project progress."""
    tracker = Tracker()
    summary = tracker.get_status_summary()

    click.echo(click.style("Project Status Summary", bold=True, fg='cyan'))
    click.echo("=" * 25)

    click.echo(click.style("\nItem Counts:", bold=True))
    for item_type, counts in summary["item_counts"].items():
        if counts["total"] > 0:
            click.echo(f"- {item_type}s: {counts['completed']} completed / {counts['total']} total")

    if summary["overdue_actions"]:
        click.echo(click.style("\nOverdue Actions:", bold=True, fg='red'))
        for action in summary["overdue_actions"]:
            due_date = datetime.fromisoformat(action['due_date']).strftime('%Y-%m-%d')
            click.echo(f"- Path: {action['path']} (Due: {due_date})")
    else:
        click.echo(click.style("\nNo overdue actions.", fg='green'))

    if summary["orphaned_items"]:
        click.echo(click.style("\nOrphaned Items:", bold=True, fg='yellow'))
        click.echo("(Items whose parent is completed, but they are not)")
        for item in summary["orphaned_items"]:
            click.echo(f"- Path: {item['path']} (Type: {item['type']})")
    else:
        click.echo(click.style("\nNo orphaned items found.", fg='green'))

    click.echo("\n" + "=" * 25)
