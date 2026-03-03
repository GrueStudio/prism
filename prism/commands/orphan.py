"""
Orphan command group for new Prism CLI.

Commands for managing orphan ideas that can be adopted into the project structure.
"""
import json
from typing import Optional

import click

from prism.core import PrismCore


@click.group()
def orphan():
    """Manage orphan ideas.

    Orphans are ideas that can be adopted into the project structure
    as phases, milestones, objectives, deliverables, or actions.
    """
    pass


@orphan.command(name="list")
@click.option(
    "-j", "--json", "json_output", is_flag=True, help="Output in JSON format."
)
def list_orphans(json_output: bool):
    """List all orphan ideas.

    Orphans are stored in .prism/orphans.json and can be adopted
    into the project structure at any level.
    
    Use the numeric ID with 'prism orphan show <ID>' to view details.
    """
    core = PrismCore()
    orphans = core.list_orphans()

    if not orphans:
        click.echo("No orphan ideas found.")
        return

    # Sort by priority descending
    orphans = sorted(orphans, key=lambda o: o.priority, reverse=True)

    if json_output:
        data = [orphan.model_dump(mode="json") for orphan in orphans]
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Orphan Ideas ({len(orphans)}):")
        click.echo("-" * 50)
        for orphan in orphans:
            click.echo(f"[{orphan.id}] {orphan.name}")
            click.echo(f"    Priority: {orphan.priority}")
            if orphan.description:
                click.echo(f"    Description: {orphan.description}")
            click.echo()


@orphan.command(name="show")
@click.argument("orphan_id")
@click.option(
    "-j", "--json", "json_output", is_flag=True, help="Output in JSON format."
)
def show_orphan(orphan_id: str, json_output: bool):
    """Show details for an orphan idea.

    ORPHAN_ID can be the numeric ID, UUID, or name of the orphan.
    """
    core = PrismCore()
    orphan = core.get_orphan(orphan_id)

    if not orphan:
        raise click.ClickException(
            f"Orphan '{orphan_id}' not found. Use 'prism orphan list' to see all orphans."
        )

    if json_output:
        click.echo(json.dumps(orphan.model_dump(mode="json"), indent=2))
    else:
        click.echo(f"ID: {orphan.id}")
        click.echo(f"Name: {orphan.name}")
        click.echo(f"UUID: {orphan.uuid}")
        click.echo(f"Priority: {orphan.priority}")
        click.echo(f"Description: {orphan.description or 'N/A'}")


@orphan.command(name="add")
@click.option("-n", "--name", required=True, help="Orphan idea name.")
@click.option("-d", "--desc", help="Orphan idea description.")
@click.option("-p", "--priority", type=int, default=0, help="Priority value (default: 0).")
def add_orphan(name: str, desc: Optional[str], priority: int):
    """Add a new orphan idea."""
    core = PrismCore()
    new_orphan = core.add_orphan(name=name, description=desc or "", priority=priority)
    click.echo(f"Orphan '{name}' added successfully.")
    click.echo(f"UUID: {new_orphan.uuid}")


@orphan.command(name="adopt")
@click.argument("orphan_id")
@click.option("-t", "--type", required=True,
              type=click.Choice(['phase', 'milestone', 'objective', 'deliverable', 'action']),
              help="Type to adopt as.")
@click.option("-p", "--parent-path", help="Parent path for the adopted item.")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def adopt_orphan(orphan_id: str, type: str, parent_path: Optional[str], yes: bool):
    """Adopt an orphan idea into the project structure.

    ORPHAN_ID can be the numeric ID, UUID, or name of the orphan.
    
    The orphan is converted to the specified type and added to the project tree.
    After adoption, the orphan is removed from the orphans list.
    
    Use -y/--yes to skip the confirmation prompt.
    """
    core = PrismCore()
    orphan = core.get_orphan(orphan_id)

    if not orphan:
        raise click.ClickException(
            f"Orphan '{orphan_id}' not found. Use 'prism orphan list' to see all orphans."
        )

    if not yes:
        click.confirm(
            f"Adopt '{orphan.name}' as a {type}?" +
            (f" Parent: {parent_path}" if parent_path else ""),
            abort=True
        )

    # Add the item to the project tree
    new_item = core.add_item(
        item_type=type,
        name=orphan.name,
        description=orphan.description,
        parent_path=parent_path,
    )

    # Remove the orphan after successful adoption
    core.remove_orphan(orphan.uuid)

    item_path = core.navigator.get_item_path(new_item)
    click.echo(f"Adopted '{orphan.name}' as {type}: {item_path}")


@orphan.command(name="delete")
@click.argument("orphan_id")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def delete_orphan(orphan_id: str, yes: bool):
    """Delete an orphan idea.

    ORPHAN_ID can be the numeric ID, UUID, or name of the orphan.
    
    Use -y/--yes to skip the confirmation prompt.
    """
    core = PrismCore()
    orphan = core.get_orphan(orphan_id)

    if not orphan:
        raise click.ClickException(
            f"Orphan '{orphan_id}' not found. Use 'prism orphan list' to see all orphans."
        )

    if not yes:
        click.confirm(f"Are you sure you want to delete orphan '{orphan.name}'?", abort=True)

    removed = core.remove_orphan(orphan.uuid)
    if removed:
        click.echo(f"Orphan '{orphan.name}' deleted successfully.")
    else:
        raise click.ClickException(f"Failed to delete orphan '{orphan_id}'.")
