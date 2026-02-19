"""
Config command group for new Prism CLI (stubs).

Commands for viewing and editing project configuration.
TODO: Implement full config management.
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
    click.echo(f"Config set - TODO: Implement")
    click.echo(f"Would set {key} = {value}")


@config.command(name="get")
@click.argument("key")
def get_config(key):
    """Get a configuration value."""
    click.echo(f"Config get - TODO: Implement")
    click.echo(f"Would get value for {key}")
