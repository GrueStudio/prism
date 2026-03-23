"""
Config command group for new Prism CLI.

Commands for viewing and editing project configuration.
"""
import json
import click

from prism.core import PrismCore
from prism.models.bug import BugType

@click.group()
@click.pass_context
def config(ctx):
    """View and edit project configuration.

    Configuration is stored in .prism/config.json.
    """
    ctx.obj = PrismCore()


@config.command(name="show")
@click.pass_obj
def show_config(core: PrismCore):
    """Show current configuration."""
    config_data = core.get_config()
    click.echo(json.dumps(config_data.model_dump(mode="json"), indent=2))


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option("--add", is_flag=True, help="Add the value to a list or dict.")
@click.option("--remove", is_flag=True, help="Remove the value from a list or dict.")
@click.pass_obj
def set_config(core: PrismCore, key: str, value: str, add: bool, remove: bool):
    """Set, add to, or remove from a configuration value.

    List/dict fields that support --add/--remove:
      - slug_filler_words (string values)
      - date_formats (string values)
      - bug_types (JSON object with name/prefix/description)
      - orphan_priority_labels (JSON object with label/value)

    Examples:
      prism config set slug_max_length 50
      prism config set slug_filler_words new-word --add
      prism config set slug_filler_words old-word --remove
      prism config set date_formats "%Y-%m-%d" --add
      prism config set bug_types '{"name":"UI","prefix":"UI"}' --add
      prism config set bug_types UI --remove
      prism config set orphan_priority_labels '{"label":"urgent","value":25}' --add
      prism config set orphan_priority_labels urgent --remove
    """
    if add and remove:
        raise click.UsageError("Cannot use --add and --remove at the same time.")

    config_data = core.get_config()

    if not hasattr(config_data, key):
        raise click.BadParameter(f"Configuration key '{key}' not found.")

    current_value = getattr(config_data, key)

    if add:
        if isinstance(current_value, list):
            if key == "bug_types":
                try:
                    bug_type_data = json.loads(value)
                    new_bug_type = BugType(**bug_type_data)
                    # Check for duplicates
                    if any(bt.prefix == new_bug_type.prefix for bt in current_value):
                        raise click.ClickException(f"Bug type with prefix '{new_bug_type.prefix}' already exists.")
                    current_value.append(new_bug_type)
                except json.JSONDecodeError:
                    raise click.BadParameter("Invalid JSON format for bug type.")
                except Exception as e:
                    raise click.ClickException(f"Error creating bug type: {e}")
            else:
                # String list (slug_filler_words, date_formats, etc.)
                if value in current_value:
                    raise click.ClickException(f"Value '{value}' already exists in '{key}'.")
                current_value.append(value)

        elif isinstance(current_value, dict):
            if key == "orphan_priority_labels":
                try:
                    label_data = json.loads(value)
                    if not isinstance(label_data, dict) or "label" not in label_data or "value" not in label_data:
                        raise click.BadParameter("JSON must contain 'label' and 'value' keys.")
                    label_name = label_data["label"]
                    label_value = int(label_data["value"])
                    if label_name in current_value:
                        raise click.ClickException(f"Label '{label_name}' already exists in '{key}'.")
                    current_value[label_name] = label_value
                except json.JSONDecodeError:
                    raise click.BadParameter("Invalid JSON format for priority label.")
                except ValueError as e:
                    raise click.BadParameter(f"Invalid value for priority: {e}")
            else:
                raise click.UsageError(f"Add operation not supported for dict key '{key}'.")
        else:
            raise click.UsageError(f"Cannot use --add on non-list/non-dict key '{key}'.")

        click.echo(f"Added value to '{key}'.")

    elif remove:
        if isinstance(current_value, list):
            if key == "bug_types":
                # Remove by prefix
                original_len = len(current_value)
                new_list = [bt for bt in current_value if bt.prefix != value]
                if len(new_list) == original_len:
                    raise click.ClickException(f"Bug type with prefix '{value}' not found.")
                setattr(config_data, key, new_list)
            else:
                # String list
                try:
                    current_value.remove(value)
                except ValueError:
                    raise click.ClickException(f"Value '{value}' not found in '{key}'.")

        elif isinstance(current_value, dict):
            if key == "orphan_priority_labels":
                if value not in current_value:
                    raise click.ClickException(f"Label '{value}' not found in '{key}'.")
                del current_value[value]
            else:
                raise click.UsageError(f"Remove operation not supported for dict key '{key}'.")
        else:
            raise click.UsageError(f"Cannot use --remove on non-list/non-dict key '{key}'.")

        click.echo(f"Removed value from '{key}'.")

    else:
        # Simple set operation
        try:
            # Try to convert to the correct type
            field_type = type(getattr(config_data, key))
            setattr(config_data, key, field_type(value))
        except (ValueError, TypeError):
            raise click.BadParameter(f"Invalid value type for key '{key}'.")

        click.echo(f"Set '{key}' to '{value}'.")

    core.save_config(config_data)
    click.echo("Configuration saved.")

