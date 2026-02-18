"""
New CLI for Prism using .prism/ folder-based storage.

This is the new CLI that will replace cli.py after testing.
Uses NewPrismCore and managers exclusively.
"""
import click

from prism.commands.crud import crud
from prism.commands.task_new import task
from prism.commands.config import config
from prism.commands.orphan import orphan
# TODO: Add new status command


@click.group()
def newcli():
    """A command-line interface for project management and task tracking (new storage)."""
    pass


newcli.add_command(crud)
newcli.add_command(task)
newcli.add_command(config)
newcli.add_command(orphan)
# TODO: newcli.add_command(status)


if __name__ == '__main__':
    newcli()
