"""
Config command group for new Prism CLI.

Commands for viewing and editing project configuration.
"""
import json
import click

from prism.core import PrismCore

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
    # Use the underlying model for JSON output
    config_data = core.config.get_model()
    click.echo(json.dumps(config_data.model_dump(mode="json"), indent=2))


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option("--add", is_flag=True, help="Add the value to a list.")
@click.option("--remove", is_flag=True, help="Remove the value from a list or dict.")
@click.pass_obj
def set_config(core: PrismCore, key: str, value: str, add: bool, remove: bool):
    """Set, add to, or remove from a configuration value.

    List/dict fields that support --add/--remove:
      - slug_filler_words (string values)
      - date_formats (string values)
      - bug_types (JSON object with name/prefix/description)
      - orphan_priority_labels (key-value via --add or key via --remove)

    Examples:
      prism config set slug_max_length 50
      prism config set slug_filler_words new-word --add
      prism config set slug_filler_words old-word --remove
      prism config set bug_types '{"name":"UI","prefix":"UI"}' --add
      prism config set bug_types UI --remove
      prism config set orphan_priority_labels '{"label":"urgent","value":25}' --add
      prism config set orphan_priority_labels urgent --remove
    """
    if add and remove:
        raise click.UsageError("Cannot use --add and --remove at the same time.")

    try:
        if add:
            if key == "orphan_priority_labels":
                # Special handling for dict-based labels in the CLI
                try:
                    data = json.loads(value)
                    if not isinstance(data, dict) or "label" not in data or "value" not in data:
                        raise click.BadParameter("JSON must contain 'label' and 'value' keys.")
                    core.config.update_dict(key, data["label"], data["value"])
                except json.JSONDecodeError:
                    raise click.BadParameter("Invalid JSON format for priority label.")
            else:
                core.config.add(key, value)
            click.echo(f"Added value to '{key}'.")

        elif remove:
            if key == "orphan_priority_labels":
                core.config.remove_from_dict(key, value)
            else:
                core.config.remove(key, value)
            click.echo(f"Removed value from '{key}'.")

        else:
            # Simple set
            core.config.set(key, value)
            click.echo(f"Set '{key}' to '{value}'.")

        click.echo("Configuration saved.")

    except (AttributeError, KeyError) as e:
        raise click.BadParameter(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error updating configuration: {e}")
