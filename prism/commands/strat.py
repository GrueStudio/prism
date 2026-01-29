import click
from prism.tracker import Tracker

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
            click.echo(f"Error: Item not found at path '{path_str}'.", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

