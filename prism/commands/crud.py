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
from prism.exceptions import (
    InvalidOperationError,
    NotFoundError,
    PrismError,
    ValidationError,
)
from prism.models.base import Action, Deliverable, Milestone, Objective, Phase


@click.group()
def crud():
    """Manage all project items (phases, milestones, objectives, deliverables, actions)."""
    pass


@crud.command(name="nav")
@click.argument("path", required=False)
def nav(path: Optional[str]):
    """Navigate to a position in the project tree.
    
    PATH can be:
    - A path (e.g., 1/2/1/deliverable-1)
    - A special token:
      - :u, :up, :parent - Go to parent
      - :cp, :current-phase - Current phase
      - :cm, :current-milestone - Current milestone
      - :co, :current-objective - Current objective
      - :cd, :current-deliverable - Current deliverable
      - :ca, :current-action - Current action (task cursor)
      - :lp, :last-phase - Last phase
      - :lm, :last-milestone - Last milestone
      - :lo, :last-objective - Last objective
      - :ld, :last-deliverable - Last deliverable
      - :la, :last-action - Last action
      - :nd, :next-deliverable - Next deliverable
      - :na, :next-action - Next action
    - Omitted to show current position
    
    Note: Navigation is restricted to paths not 'behind' the task cursor in
    depth-first order. You cannot navigate to earlier branches of the tree.
    
    Examples:
        prism crud nav                  # Show current position
        prism crud nav :u               # Go to parent
        prism crud nav :co              # Jump to current objective
        prism crud nav :lasto           # Go to last objective
        prism crud nav :nextd           # Go to next deliverable
        prism crud nav 1/2/1/deliverable-1
    """
    core = PrismCore()
    
    if path is None:
        # Show current position
        context = core.navigator.get_crud_context()
        if context:
            item = core.get_item_by_path(context)
            if item:
                click.echo(f"Current position: {context}")
                click.echo(f"  Type: {type(item).__name__}")
                click.echo(f"  Name: {item.name}")
            else:
                click.echo(f"Current position: {context} (item not found)")
        else:
            click.echo("No current position set.")
        return
    
    # Resolve path (handles special tokens)
    resolved = core.navigator.resolve_path(path)
    
    if not resolved:
        raise click.ClickException(f"Cannot navigate to '{path}' - path not resolved.")
    
    # Validate: path must not be behind task_cursor in depth-first order
    if core.project.task_cursor:
        if core.navigator._is_path_behind(resolved, core.project.task_cursor):
            raise click.ClickException(
                f"Cannot navigate to '{resolved}' - this path is behind the current task cursor "
                f"'{core.project.task_cursor}' in depth-first order. "
                f"You can only navigate to the current position, ancestors, or later branches."
            )
    
    # Verify item exists
    item = core.get_item_by_path(resolved)
    if not item:
        raise click.ClickException(f"Cannot navigate to '{path}' - item not found at '{resolved}'.")
    
    # Set crud_context (task_cursor is managed by TaskManager only)
    if not core.navigator.set_crud_context(resolved):
        raise click.ClickException(
            f"Failed to set CRUD context to '{resolved}'. "
            f"The path must not be behind the current task cursor."
        )
    core._save_project()
    
    click.echo(f"Navigated to: {resolved}")
    click.echo(f"  Type: {type(item).__name__}")
    click.echo(f"  Name: {item.name}")


def _get_item_by_path_or_uuid(
    core: PrismCore,
    path: Optional[str],
    uuid: Optional[str],
    require_path: bool = False,
):
    """Get an item by path or UUID.

    For show/edit/delete commands.

    Args:
        core: PrismCore instance
        path: Path string (positional, optional). Empty string means current position.
        uuid: UUID string (optional flag)
        require_path: If True, errors when no path provided (for edit/delete safety)

    Returns:
        The item if found

    Raises:
        click.ClickException: If neither path nor uuid provided, or item not found
    """
    if uuid:
        # Lookup by UUID
        item = core.project.get_item(uuid)
        if not item:
            raise click.ClickException(f"Item with UUID '{uuid}' not found.")
        return item

    if not path:
        if require_path:
            raise click.ClickException(
                "Path required. Please specify the item path to modify."
            )
        # Default to current position for show
        context = core.navigator.get_crud_context()
        if context:
            item = core.get_item_by_path(context)
            if item:
                return item
        raise click.ClickException(
            "No path provided and no current position set. Please specify a path."
        )

    # Resolve path (handles special tokens and relative paths)
    resolved = core.navigator.resolve_path(path)
    
    try:
        item = core.get_item_by_path(resolved)
        if not item:
            raise NotFoundError(f"Item not found at path '{resolved}'.")
        return item
    except NotFoundError as e:
        raise click.ClickException(str(e))


def _get_parent_path_for_add(
    core: PrismCore, item_type: str, parent_path: Optional[str]
) -> Optional[str]:
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
        # Resolve parent path (handles special tokens and relative paths)
        return core.navigator.resolve_path(parent_path)

    # Phase has no parent
    if item_type == "phase":
        return None

    # For other types, infer from current context
    current_context = core.navigator.get_crud_context()
    
    if item_type == "milestone":
        # Need a phase to add milestone to
        if current_context:
            context_item = core.get_item_by_path(current_context)
            if context_item and isinstance(context_item, Phase):
                return current_context
        current_phase = core.navigator.get_current_phase()
        if current_phase:
            return core.navigator.get_item_path(current_phase)
        raise click.ClickException(
            f"Cannot add {item_type} without a parent. Please specify -p/--parent-path."
        )

    if item_type == "objective":
        # Need a milestone to add objective to
        if current_context:
            context_item = core.get_item_by_path(current_context)
            if context_item and isinstance(context_item, Milestone):
                return current_context
        current_milestone = core.navigator.get_current_milestone()
        if current_milestone:
            return core.navigator.get_item_path(current_milestone)
        raise click.ClickException(
            f"Cannot add {item_type} without a parent. Please specify -p/--parent-path."
        )

    if item_type in ("deliverable", "action"):
        # Use current objective for deliverable, or its deliverables for action
        if current_context:
            context_item = core.get_item_by_path(current_context)
            if item_type == "deliverable":
                if context_item and isinstance(context_item, Objective):
                    return current_context
            else:  # action
                if context_item and isinstance(context_item, Deliverable):
                    return current_context
        
        current_objective = core.navigator.get_current_objective()
        if current_objective:
            if item_type == "deliverable":
                return core.navigator.get_item_path(current_objective)
            else:
                # For action, need to find current deliverable
                # Default to first pending deliverable
                for deliv in current_objective.children:
                    if deliv.status != "completed":
                        return f"{core.navigator.get_item_path(current_objective)}/{deliv.slug}"
                # Fallback to last deliverable
                if current_objective.children:
                    last_deliv = current_objective.children[-1]
                    return f"{core.navigator.get_item_path(current_objective)}/{last_deliv.slug}"

        raise click.ClickException(
            f"Cannot add {item_type} without a parent. "
            "Please specify -p/--parent-path or set a current task."
        )

    return None


def _serialize_item(item) -> dict:
    """Serialize any item to a dict for JSON output."""
    return item.model_dump(mode="json")


def _display_item(item, show_children: bool = True):
    """Display item details in human-readable format."""
    click.echo(f"Name: {item.name}")
    click.echo(f"Description: {item.description or ''}")
    click.echo(f"Status: {item.status}")
    click.echo(f"Type: {type(item).__name__}")

    if not show_children:
        return

    # Display children based on item type - all items now use .children property
    children = []
    child_type = ""

    if isinstance(item, Phase):
        children = [(m.name, m.slug) for m in item.children]
        child_type = "Milestones"
    elif hasattr(item, "item_type") and item.item_type == "phase":  # ArchivedItem
        children = [(m.name, m.slug) for m in item.children]
        child_type = "Milestones"
    elif isinstance(item, Milestone):
        children = [(o.name, o.slug) for o in item.children]
        child_type = "Objectives"
    elif hasattr(item, "item_type") and item.item_type == "milestone":  # ArchivedItem
        children = [(o.name, o.slug) for o in item.children]
        child_type = "Objectives"
    elif isinstance(item, Objective):
        children = [(d.name, d.slug) for d in item.children]
        child_type = "Deliverables"
    elif hasattr(item, "item_type") and item.item_type == "objective":  # ArchivedItem
        children = [(d.name, d.slug) for d in item.children]
        child_type = "Deliverables"
    elif isinstance(item, Deliverable):
        children = [(a.name, a.slug) for a in item.children]
        child_type = "Actions"
    elif hasattr(item, "item_type") and item.item_type == "deliverable":  # ArchivedItem
        children = [(a.name, a.slug) for a in item.children]
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
@click.option(
    "-j", "--json", "json_output", is_flag=True, help="Output in JSON format."
)
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

            # Add children based on item type - all items now use .children
            if isinstance(item, Phase):
                item_dict["children"] = [_serialize_item(m) for m in item.children]
            elif isinstance(item, Milestone):
                item_dict["children"] = [_serialize_item(o) for o in item.children]
            elif isinstance(item, Objective):
                item_dict["children"] = [_serialize_item(d) for d in item.children]
            elif isinstance(item, Deliverable):
                item_dict["children"] = [_serialize_item(a) for a in item.children]

            click.echo(json.dumps(item_dict, indent=2))
        else:
            _display_item(item)

    except NotFoundError as e:
        raise click.ClickException(str(e))
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")


@crud.command(name="add")
@click.argument("path", required=False)
@click.option(
    "-t",
    "--type",
    "item_type",
    required=True,
    type=click.Choice(["phase", "milestone", "objective", "deliverable", "action"]),
    help="Item type to add.",
)
@click.option("-n", "--name", required=True, help="Item name.")
@click.option("-d", "--desc", help="Item description.")
@click.option("-s", "--status", help="Initial status (default: pending).")
@click.option(
    "-p", "--parent-path", help="Parent item path (auto-inferred if omitted)."
)
@click.option("--nav", is_flag=True, help="Navigate to created item.")
def add(
    path: Optional[str],
    item_type: str,
    name: str,
    desc: Optional[str],
    status: Optional[str],
    parent_path: Optional[str],
    nav: bool,
):
    """Add a new project item.

    Item type determines what can be added:
    - phase: Top-level only (no parent)
    - milestone: Parent must be phase
    - objective: Parent must be milestone
    - deliverable: Parent must be objective
    - action: Parent must be deliverable

    If parent path is omitted, it's inferred from current context.
    Use --nav to navigate to the created item.
    """
    core = PrismCore()
    try:
        # Resolve parent path
        if item_type != "phase":
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

        new_item = core.add_item(
            item_type=item_type,
            name=name,
            description=desc,
            parent_path=resolved_parent,
            status=status,
        )
        
        # Navigate to created item if requested
        if nav:
            item_path = core.navigator.get_item_path(new_item)
            if item_path:
                core.project.task_cursor = item_path
                core.project.crud_context = item_path
                core._save_project()
                click.echo(f"{item_type.capitalize()} '{name}' created and navigating to: {item_path}")
            else:
                click.echo(f"{item_type.capitalize()} '{name}' created successfully.")
        else:
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
def edit(
    path: Optional[str],
    uuid: Optional[str],
    name: Optional[str],
    desc: Optional[str],
    status: Optional[str],
):
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

        core.update_item(path=item_path, name=name, description=desc, status=status)
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
