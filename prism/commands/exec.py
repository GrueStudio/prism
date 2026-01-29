import click
from prism.tracker import Tracker
from pathlib import Path
import json

@click.group(name='exec')
def exec():
    """Manage execution project items (deliverables, actions)."""
    pass

@exec.command(name='add')
@click.option('--deliverable', 'item_type', flag_value='deliverable', help='Add a new deliverable.')
@click.option('--action', 'item_type', flag_value='action', help='Add a new action.')
@click.option('--name', required=True, help='The name of the item.')
@click.option('--desc', help='A description for the item.')
@click.option('--parent-path', help='The path to the parent item.')
def add(item_type, name, desc, parent_path):
    """Adds a new execution item."""
    if not item_type:
        raise click.ClickException("Please specify an item type to add.")

    tracker = Tracker()
    try:
        tracker.add_item(
            item_type=item_type,
            name=name,
            description=desc,
            parent_path=parent_path
        )
        click.echo(f"{item_type.capitalize()} '{name}' created successfully.")
    except Exception as e:
        raise click.ClickException(f"Error: {e}")

@exec.command(name='show')
@click.option('--path', 'path_str', required=True, help='The path to the item to show.')
def show(path_str):
    """Shows details for an execution item."""
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

@exec.command(name='addtree')
@click.argument('json_file_path', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--mode', type=click.Choice(['append', 'replace'], case_sensitive=False), default='append', help='Mode for adding the execution tree.')
def addtree(json_file_path, mode):
    """Adds an entire execution tree from a JSON file."""
    tracker = Tracker()
    try:
        file_path = Path(json_file_path)
        with open(file_path, 'r') as f:
            tree_data = json.load(f)
        
        tracker.add_exec_tree(tree_data, mode)
        click.echo(f"Execution tree added successfully in '{mode}' mode.")
    except FileNotFoundError:
        raise click.ClickException(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON format in '{json_file_path}': {e}")
    except Exception as e:
        raise click.ClickException(f"Error adding execution tree: {e}")

