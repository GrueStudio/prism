import click
from prism.tracker import Tracker

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
        click.echo("Error: Please specify an item type to add.", err=True)
        return

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
        click.echo(f"Error: {e}", err=True)

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
            click.echo(f"Error: Item not found at path '{path_str}'.", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

