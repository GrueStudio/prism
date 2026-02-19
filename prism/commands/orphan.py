"""
Orphan command group for new Prism CLI (stubs).

Commands for managing orphan ideas that can be adopted into the project structure.
TODO: Implement full orphan management.
"""
import click


@click.group()
def orphan():
    """Manage orphan ideas.

    Orphans are ideas that can be adopted into the project structure
    as phases, milestones, objectives, deliverables, or actions.
    """
    pass


@orphan.command(name="list")
def list_orphans():
    """List all orphan ideas."""
    click.echo("Orphan list - TODO: Implement")
    click.echo("Orphans are stored in .prism/orphans.json")


@orphan.command(name="add")
@click.option("-n", "--name", required=True, help="Orphan idea name.")
@click.option("-d", "--desc", help="Orphan idea description.")
def add_orphan(name, desc):
    """Add a new orphan idea."""
    click.echo("Orphan add - TODO: Implement")
    click.echo(f"Would add orphan: {name}")


@orphan.command(name="adopt")
@click.argument("orphan_id")
@click.option("-t", "--type", required=True, 
              type=click.Choice(['phase', 'milestone', 'objective', 'deliverable', 'action']),
              help="Type to adopt as.")
@click.option("-p", "--parent-path", help="Parent path for the adopted item.")
def adopt_orphan(orphan_id, type, parent_path):
    """Adopt an orphan idea into the project structure."""
    click.echo("Orphan adopt - TODO: Implement")
    click.echo(f"Would adopt {orphan_id} as {type}")


@orphan.command(name="delete")
@click.argument("orphan_id")
@click.confirmation_option(prompt="Are you sure you want to delete this orphan?")
def delete_orphan(orphan_id):
    """Delete an orphan idea."""
    click.echo("Orphan delete - TODO: Implement")
    click.echo(f"Would delete orphan: {orphan_id}")
