import json
import uuid
from datetime import datetime
from pathlib import Path

import click

from prism.core import Core
from prism.exceptions import PrismError, NotFoundError, ValidationError, InvalidOperationError


@click.group(name="exec")
def exec():
    """Manage execution project items (deliverables, actions)."""
    pass


@exec.command(name="add")
@click.option(
    "--deliverable",
    "item_type",
    flag_value="deliverable",
    help="Add a new deliverable.",
)
@click.option("--action", "item_type", flag_value="action", help="Add a new action.")
@click.option("--name", required=True, help="The name of the item.")
@click.option("--desc", help="A description for the item.")
@click.option("--parent-path", help="The path to the parent item.")
def add(item_type, name, desc, parent_path):
    """Adds a new execution item."""
    if not item_type:
        raise click.ClickException("Please specify an item type to add.")

    core = Core()
    try:
        core.add_item(
            item_type=item_type,
            name=name,
            description=desc,
            parent_path=parent_path,
            status=None,
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


@exec.command(name="show")
@click.option("--path", "path_str", required=True, help="The path to the item to show.")
@click.option(
    "--json", "json_output", is_flag=True, help="Output item details in JSON format."
)
def show(path_str, json_output):
    """Shows details for an execution item."""
    core = Core()
    try:
        item = core.navigator.get_item_by_path(path_str)
        if not item:
            raise NotFoundError(f"Item not found at path '{path_str}'.")

        if json_output:
            item_dict = item.model_dump()
            # Convert UUID and datetime objects to strings for JSON serialization
            for key, value in item_dict.items():
                if isinstance(value, uuid.UUID):
                    item_dict[key] = str(value)
                elif isinstance(value, datetime):
                    item_dict[key] = value.isoformat()

            click.echo(json.dumps(item_dict, indent=2))
        else:
            click.echo(f"Name: {item.name}")
            click.echo(f"Description: {item.description}")
            click.echo(f"Status: {item.status}")
            click.echo(f"Type: {type(item).__name__}")
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")


@exec.command(name="addtree")
@click.argument(
    "json_file_path", type=click.Path(exists=True, dir_okay=False, readable=True)
)
@click.option(
    "--mode",
    type=click.Choice(["append", "replace"], case_sensitive=False),
    default="append",
    help="Mode for adding the execution tree.",
)
def addtree(json_file_path, mode):
    """Adds an entire execution tree from a JSON file."""
    core = Core()
    try:
        file_path = Path(json_file_path)
        with open(file_path, "r") as f:
            tree_data = json.load(f)

        core.add_exec_tree(tree_data, mode)
        click.echo(f"Execution tree added successfully in '{mode}' mode.")
    except FileNotFoundError:
        raise click.ClickException(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON format in '{json_file_path}': {e}")
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except ValidationError as e:
        raise click.ClickException(f"Validation Error: {e}")
    except InvalidOperationError as e:
        raise click.ClickException(f"Operation Error: {e}")
    except PrismError as e:
        raise click.ClickException(f"Error adding execution tree: {e}")


@exec.command(name="edit")
@click.option("--path", "path_str", required=True, help="The path to the item to edit.")
@click.option("--name", help="New name for the item.")
@click.option("--desc", help="New description for the item.")
@click.option("--due-date", help="New due date for the item (YYYY-MM-DD).")
@click.option(
    "--file",
    "json_file_path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a JSON file containing update data.",
)
def edit(path_str, name, desc, due_date, json_file_path):
    """Edits an execution item."""
    update_data = {}
    if json_file_path:
        try:
            with open(Path(json_file_path), "r") as f:
                file_data = json.load(f)
            update_data.update(file_data)
        except json.JSONDecodeError as e:
            raise click.ClickException(
                f"Error: Invalid JSON format in '{json_file_path}': {e}"
            )
        except (
            FileNotFoundError
        ):  # Should be caught by click.Path(exists=True) but good for safety
            raise click.ClickException(f"Error: File '{json_file_path}' not found.")

    if name is not None:
        update_data["name"] = name
    if desc is not None:
        update_data["description"] = desc
    if due_date is not None:
        update_data["due_date"] = due_date

    if not update_data:
        raise click.ClickException(
            "No update parameters provided. Use --name, --desc, --due-date, or --file."
        )

    core = Core()
    try:
        core.update_item(path=path_str, **update_data, status=None)
        click.echo(f"Item at '{path_str}' updated successfully.")
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except ValidationError as e:
        raise click.ClickException(f"Validation Error: {e}")
    except InvalidOperationError as e:
        raise click.ClickException(f"Operation Error: {e}")
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")


@exec.command(name="delete")
@click.option(
    "--path", "path_str", required=True, help="The path to the item to delete."
)
def delete(path_str):
    """Deletes an execution item."""
    core = Core()
    try:
        core.delete_item(path=path_str)
        click.echo(f"Item at '{path_str}' deleted successfully.")
    except NotFoundError as e:
        raise click.ClickException(str(e))
    except InvalidOperationError as e:
        raise click.ClickException(f"Operation Error: {e}")
    except PrismError as e:
        raise click.ClickException(f"Error: {e}")
