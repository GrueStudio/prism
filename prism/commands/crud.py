"""
Unified CRUD commands for Prism CLI using PrismCore.

Handles all strategic and execution items through a single interface.
Path is positional argument, UUID is optional flag.
"""
import json
from pathlib import Path
from typing import Optional

import click

from prism.core import PrismCore
from prism.models.strategic import Phase, Milestone, Objective
from prism.models.execution import Deliverable, Action
from prism.exceptions import (
    PrismError, NotFoundError, ValidationError, InvalidOperationError
)


@click.group()
def crud():
    """Manage all project items (phases, milestones, objectives, deliverables, actions)."""
    pass


def _get_item_by_path_or_uuid(core: PrismCore, path: Optional[str], uuid: Optional[str], require_path: bool = False):
    """Get an item by path or UUID.
    
    For show/edit/delete commands.
    
    Args:
        core: PrismCore instance
        path: Path string (positional, optional)
        uuid: UUID string (optional flag)
        require_path: If True, errors when no path provided (for edit/delete safety)
    
    Returns:
        The item if found
    
    Raises:
        click.ClickException: If neither path nor uuid provided, or item not found
    """
    if uuid:
        # Lookup by UUID
        item = core.project.get_by_uuid(uuid)
        if not item:
            raise click.ClickException(f"Item with UUID '{uuid}' not found.")
        return item
    
    if not path:
        if require_path:
            raise click.ClickException(
                "Path required. Please specify the item path to modify."
            )
        # Default to current phase for show
        current_phase = core.navigator.get_current_phase()
        if current_phase:
            return current_phase
        raise click.ClickException(
            "No path provided and no current phase found. "
            "Please specify a path."
        )
    
    try:
        item = core.navigator.get_item_by_path(path)
        if not item:
            raise NotFoundError(f"Item not found at path '{path}'.")
        return item
    except NotFoundError as e:
        raise click.ClickException(str(e))


def _get_parent_path_for_add(core: PrismCore, item_type: str, parent_path: Optional[str]) -> Optional[str]:
    """Get parent path for add command, inferring from context based on item type.
    
    Args:
        core: PrismCore instance
        item_type: Type of item being added
        parent_path: Explicit parent path (optional)
    
    Returns:
        Parent path string or None for top-level
    
    Raises:
        click.ClickException: If parent cannot be inferred
    """
    if parent_path:
        return parent_path
    
    # Phase has no parent
    if item_type == 'phase':
        return None
    
    # For other types, infer from current context
    current_objective = core.navigator.get_current_objective()
    
    if item_type == 'milestone':
        # Need a phase to add milestone to
        current_phase = core.navigator.get_current_phase()
        if current_phase:
            return core.navigator.get_item_path(current_phase)
        raise click.ClickException(
            f"Cannot add {item_type} without a parent. "
            "Please specify -p/--parent-path."
        )
    
    if item_type == 'objective':
        # Need a milestone to add objective to
        current_milestone = core.navigator.get_current_milestone()
        if current_milestone:
            return core.navigator.get_item_path(current_milestone)
        raise click.ClickException(
            f"Cannot add {item_type} without a parent. "
            "Please specify -p/--parent-path."
        )
    
    if item_type in ('deliverable', 'action'):
        # Use current objective for deliverable, or its deliverables for action
        if current_objective:
            if item_type == 'deliverable':
                return core.navigator.get_item_path(current_objective)
            else:
                # For action, need to find current deliverable
                # Default to first pending deliverable
                for deliv in current_objective.deliverables:
                    if deliv.status != 'completed':
                        return f"{core.navigator.get_item_path(current_objective)}/{deliv.slug}"
                # Fallback to last deliverable
                if current_objective.deliverables:
                    last_deliv = current_objective.deliverables[-1]
                    return f"{core.navigator.get_item_path(current_objective)}/{last_deliv.slug}"
        
        raise click.ClickException(
            f"Cannot add {item_type} without a parent. "
            "Please specify -p/--parent-path or set a current task."
        )
    
    return None


def _serialize_item(item) -> dict:
    """Serialize any item to a dict for JSON output."""
    return item.model_dump(mode='json')


def _display_item(item, show_children: bool = True):
    """Display item details in human-readable format."""
    click.echo(f"Name: {item.name}")
    click.echo(f"Description: {item.description or ''}")
    click.echo(f"Status: {item.status}")
    click.echo(f"Type: {type(item).__name__}")

    if not show_children:
        return

    # Display children based on item type - handle both real objects and ArchivedItem wrappers
    children = []
    child_type = ""

    if isinstance(item, Phase):
        children = [(m.name, m.slug) for m in item.milestones]
        child_type = "Milestones"
    elif hasattr(item, 'item_type') and item.item_type == 'phase':  # ArchivedItem
        children = [(m.name, m.slug) for m in item.children]
        child_type = "Milestones"
    elif isinstance(item, Milestone):
        children = [(o.name, o.slug) for o in item.objectives]
        child_type = "Objectives"
    elif hasattr(item, 'item_type') and item.item_type == 'milestone':  # ArchivedItem
        children = [(o.name, o.slug) for o in item.children]
        child_type = "Objectives"
    elif isinstance(item, Objective):
        children = [(d.name, d.slug) for d in item.deliverables]
        child_type = "Deliverables"
    elif hasattr(item, 'item_type') and item.item_type == 'objective':  # ArchivedItem
        children = [(d.name, d.slug) for d in item.get_deliverables()]
        child_type = "Deliverables"
    elif isinstance(item, Deliverable):
        children = [(a.name, a.slug) for a in item.actions]
        child_type = "Actions"
    elif hasattr(item, 'item_type') and item.item_type == 'deliverable':  # ArchivedItem
        children = [(a.name, a.slug) for a in item.get_actions()]
        child_type = "Actions"

    if children:
        click.echo(f"\n{child_type}:")
        for i, (name, slug) in enumerate(children, 1):
            click.echo(f"  {i}. {name} ({slug})")
    else:
        click.echo(f"\nNo {child_type.lower()}.")


@crud.command(name="show")
@click.argument("path", required=False)
@click.option("-u", "--uuid", help="Item UUID (overrides path).")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output in JSON format.")
def show(path: Optional[str], uuid: Optional[str], json_output: bool):
    """Show details for a project item.
    
    PATH is the item path (e.g., 1/2/1 or alpha/adopt-orphan-id/revamp-data-sto).
    If PATH is omitted, shows the current phase.
    Use -u/--uuid to lookup by UUID instead.
    """
    core = PrismCore()
    try:
        item = _get_item_by_path_or_uuid(core, path, uuid, require_path=False)
        
        if json_output:
            item_dict = _serialize_item(item)
            
            # Add children based on item type
            if isinstance(item, Phase):
                item_dict["milestones"] = [_serialize_item(m) for m in item.milestones]
            elif isinstance(item, Milestone):
                item_dict["objectives"] = [_serialize_item(o) for o in item.objectives]
            elif isinstance(item, Objective):
                item_dict["deliverables"] = [_serialize_item(d) for d in item.deliverables]
            elif isinstance(item, Deliverable):
                item_dict["actions"] = [_serialize_item(a) for a in item.actions]
            
            click.echo(json.dumps(item_dict, indent=2))
        else:
            _display_item(item)
            
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")


@crud.command(name="add")
@click.argument("path", required=False)
@click.option("-t", "--type", "item_type", required=True, 
              type=click.Choice(['phase', 'milestone', 'objective', 'deliverable', 'action']),
              help="Item type to add.")
@click.option("-n", "--name", required=True, help="Item name.")
@click.option("-d", "--desc", help="Item description.")
@click.option("-s", "--status", help="Initial status (default: pending).")
@click.option("-p", "--parent-path", help="Parent item path (auto-inferred if omitted).")
def add(path: Optional[str], item_type: str, name: str, desc: Optional[str], 
        status: Optional[str], parent_path: Optional[str]):
    """Add a new project item.
    
    Item type determines what can be added:
    - phase: Top-level only (no parent)
    - milestone: Parent must be phase
    - objective: Parent must be milestone
    - deliverable: Parent must be objective
    - action: Parent must be deliverable
    
    If parent path is omitted, it's inferred from current context.
    """
    core = PrismCore()
    try:
        # Resolve parent path
        if item_type != 'phase':
            resolved_parent = _get_parent_path_for_add(core, item_type, parent_path)
            if not resolved_parent:
                raise click.ClickException(
                    f"Cannot add {item_type} without a parent. "
                    "Please specify -p/--parent-path or set a current task."
                )
            
            # Validate parent type and check execution tree completion
            parent_item = core.navigator.get_item_by_path(resolved_parent)
            if not parent_item:
                raise NotFoundError(f"Parent not found at '{resolved_parent}'.")
            
            if isinstance(parent_item, Objective):
                if not core.is_exec_tree_complete(resolved_parent):
                    raise InvalidOperationError(
                        f"Cannot add strategic item. Execution tree for '{resolved_parent}' is not complete."
                    )
        else:
            resolved_parent = None
        
        core.add_item(
            item_type=item_type,
            name=name,
            description=desc,
            parent_path=resolved_parent,
            status=status
        )
        click.echo(f"{item_type.capitalize()} '{name}' created successfully.")
        
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except ValidationError as e:
        raise click.ClickException(f"Validation Error: {e}")
    except InvalidOperationError as e:
        raise click.ClickException(f"Operation Error: {e}")
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")


@crud.command(name="edit")
@click.argument("path", required=False)
@click.option("-u", "--uuid", help="Item UUID (overrides path).")
@click.option("-n", "--name", help="New name.")
@click.option("-d", "--desc", help="New description.")
@click.option("-s", "--status", help="New status.")
def edit(path: Optional[str], uuid: Optional[str], name: Optional[str], 
         desc: Optional[str], status: Optional[str]):
    """Edit an existing project item.
    
    PATH is the item path. Path is required for safety.
    Use -u/--uuid to edit by UUID instead.
    
    Only specified fields are updated.
    """
    core = PrismCore()
    try:
        item = _get_item_by_path_or_uuid(core, path, uuid, require_path=True)
        item_path = core.navigator.get_item_path(item)
        
        if not any([name, desc, status]):
            raise click.ClickException(
                "No update parameters provided. "
                "Specify at least one of: -n/--name, -d/--desc, -s/--status."
            )
        
        core.update_item(
            path=item_path,
            name=name,
            description=desc,
            status=status
        )
        click.echo(f"Item '{item.name}' updated successfully.")
        
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except ValidationError as e:
        raise click.ClickException(f"Validation Error: {e}")
    except InvalidOperationError as e:
        raise click.ClickException(f"Operation Error: {e}")
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")


@crud.command(name="delete")
@click.argument("path", required=False)
@click.option("-u", "--uuid", help="Item UUID (overrides path).")
@click.confirmation_option(prompt="Are you sure you want to delete this item?")
def delete(path: Optional[str], uuid: Optional[str]):
    """Delete a project item.
    
    PATH is the item path. Path is required for safety.
    Use -u/--uuid to delete by UUID instead.
    
    WARNING: This will delete all child items as well.
    """
    core = PrismCore()
    try:
        item = _get_item_by_path_or_uuid(core, path, uuid, require_path=True)
        item_path = core.navigator.get_item_path(item)
        
        core.delete_item(path=item_path)
        click.echo(f"Item '{item.name}' deleted successfully.")
        
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except InvalidOperationError as e:
        raise click.ClickException(f"Operation Error: {e}")
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")
