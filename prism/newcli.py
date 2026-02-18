"""
New CLI for Prism using .prism/ folder-based storage.

This is the new CLI that will replace cli.py after testing.
Uses NewPrismCore and managers exclusively.
"""
import click

from prism.commands.crud import crud
# TODO: Add new task commands
# TODO: Add new status command
# TODO: Add new config command group
# TODO: Add new orphan command group (stubs)


@click.group()
def newcli():
    """A command-line interface for project management and task tracking (new storage)."""
    pass


newcli.add_command(crud)
# TODO: newcli.add_command(task)
# TODO: newcli.add_command(status)
# TODO: newcli.add_command(config)
# TODO: newcli.add_command(orphan)


if __name__ == '__main__':
    newcli()
