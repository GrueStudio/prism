"""
New CLI for Prism using .prism/ folder-based storage.

This is the new CLI that will replace cli.py after testing.
Uses PrismCore and managers exclusively.
"""
import click

from prism.commands.crud import crud
from prism.commands.task import task
from prism.commands.status import status
from prism.commands.config import config
from prism.commands.orphan import orphan


@click.group()
def cli():
    """A command-line interface for project management and task tracking (new storage)."""
    pass


cli.add_command(crud)
cli.add_command(task)
cli.add_command(status)
cli.add_command(config)
cli.add_command(orphan)


if __name__ == '__main__':
    cli()
