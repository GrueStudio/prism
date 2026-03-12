"""
Config command group for new Prism CLI.

Commands for viewing and editing project configuration including bug types.
"""
import click


@click.group()
def config():
    """View and edit project configuration.

    Configuration is stored in .prism/config.json.
    """
    pass


@config.command(name="show")
def show_config():
    """Show current configuration."""
    click.echo("Config show - TODO: Implement")
    click.echo("Configuration is stored in .prism/config.json")


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def set_config(key, value):
    """Set a configuration value."""
    click.echo(f"Config set - TODO: Implement ({key} = {value})")


@config.command(name="get")
@click.argument("key")
def get_config(key):
    """Get a configuration value."""
    click.echo(f"Config get - TODO: Implement ({key})")


# Bug type configuration commands
@config.group(name="bug-types")
def bug_types():
    """Manage bug type configurations."""
    pass


@bug_types.command(name="list")
def list_bug_types():
    """List configured bug types."""
    click.echo("Bug types list - TODO: Implement")


@bug_types.command(name="add")
@click.option("--name", required=True, help="Bug type name.")
@click.option("--prefix", required=True, help="Bug type prefix (2-4 uppercase letters).")
@click.option("--description", help="Bug type description.")
def add_bug_type(name: str, prefix: str, description: str):
    """Add a bug type configuration."""
    click.echo(f"Bug type add - TODO: Implement ({name}: {prefix})")


@bug_types.command(name="remove")
@click.argument("prefix")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation.")
def remove_bug_type(prefix: str, yes: bool):
    """Remove a bug type configuration."""
    click.echo(f"Bug type remove - TODO: Implement ({prefix})")
