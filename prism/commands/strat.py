import click
from prism.tracker import Tracker
from prism.models import Objective
import json
from pathlib import Path

@click.group()
def strat():
    """Manage strategic project items (phases, milestones, objectives)."""
    pass

@strat.command(name='add')
@click.option('--phase', 'item_type', flag_value='phase', help='Add a new phase.')
@click.option('--milestone', 'item_type', flag_value='milestone', help='Add a new milestone.')
@click.option('--objective', 'item_type', flag_value='objective', help='Add a new objective.')
@click.option('--name', required=True, help='The name of the item.')
@click.option('--desc', help='A description for the item.')
@click.option('--parent-path', help='The path to the parent item.')
def add(item_type, name, desc, parent_path):
    """Adds a new strategic item."""
    if not item_type:
        raise click.ClickException("Please specify an item type to add.")

    tracker = Tracker()
    try:
        if parent_path:
            parent_item = tracker.get_item_by_path(parent_path)
            if not parent_item:
                raise click.ClickException(f"Parent item not found at path: {parent_path}")
            if isinstance(parent_item, Objective):
                if not tracker.is_exec_tree_complete(parent_path):
                    raise click.ClickException(f"Cannot add strategic item. Execution tree for '{parent_path}' is not complete or does not exist.")
        
        tracker.add_item(
            item_type=item_type,
            name=name,
            description=desc,
            parent_path=parent_path
        )
        click.echo(f"{item_type.capitalize()} '{name}' created successfully.")
    except Exception as e:
        raise click.ClickException(f"Error: {e}")

@strat.command(name='show')
@click.option('--path', 'path_str', required=True, help='The path to the item to show.')
def show(path_str):
    """Shows details for a strategic item."""
    tracker = Tracker()
    try:
        item = tracker.get_item_by_path(path_str)
        if item:
            click.echo(f"Name: {item.name}")
            click.echo(f"Description: {item.description}")
            click.echo(f"Status: {item.status}")
            click.echo(f"Type: {type(item).__name__}")
        else:
            raise click.ClickException(f"Item not found at path '{path_str}'.")
    except Exception as e:
        raise click.ClickException(f"Error: {e}")

@strat.command(name='edit')
@click.option('--path', 'path_str', required=True, help='The path to the item to edit.')
@click.option('--name', help='New name for the item.')
@click.option('--desc', help='New description for the item.')
@click.option('--file', 'json_file_path', type=click.Path(exists=True, dir_okay=False, readable=True), help='Path to a JSON file containing update data.')
def edit(path_str, name, desc, json_file_path):
    """Edits a strategic item."""
    update_data = {}
    if json_file_path:
        try:
            with open(Path(json_file_path), 'r') as f:
                file_data = json.load(f)
            update_data.update(file_data)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Error: Invalid JSON format in '{json_file_path}': {e}")
        except FileNotFoundError: # Should be caught by click.Path(exists=True) but good for safety
            raise click.ClickException(f"Error: File '{json_file_path}' not found.")
    
    if name is not None:
        update_data['name'] = name
    if desc is not None:
        update_data['description'] = desc

    if not update_data:
        raise click.ClickException("No update parameters provided. Use --name, --desc, or --file.")

    tracker = Tracker()
    try:
        tracker.update_item(path=path_str, **update_data, status=None) # status is removed as per the deliverable
        click.echo(f"Item at '{path_str}' updated successfully.")
    except Exception as e:
        raise click.ClickException(f"Error: {e}")

@strat.command(name='delete')
@click.option('--path', 'path_str', required=True, help='The path to the item to delete.')
def delete(path_str):
    """Deletes a strategic item."""
    tracker = Tracker()
    try:
        tracker.delete_item(path=path_str)
        click.echo(f"Item at '{path_str}' deleted successfully.")
    except Exception as e:
        raise click.ClickException(f"Error: {e}")