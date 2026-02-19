"""
DEPRECATED: Old Prism CLI using project.json storage.

This CLI is deprecated and will be removed in a future version.
Use the new CLI (prism.cli) with .prism/ folder-based storage instead.

Migration: Run `python scripts/migrate_project.py` to migrate your data.
"""
import click
import warnings

# Show deprecation warning on every use
warnings.warn(
    "The old Prism CLI (project.json storage) is deprecated and will be removed. "
    "Please migrate to the new storage system by running: python scripts/migrate_project.py",
    DeprecationWarning,
    stacklevel=2
)

from prism.commands.strat_old import strat
from prism.commands.exec_old import exec
from prism.commands.status_old import status
from prism.commands.init import init
from prism.commands.task_old import task

@click.group()
def cli():
    """[DEPRECATED] A command-line interface for project management and task tracking.
    
    This CLI uses the old project.json storage format and is deprecated.
    Use the new CLI with .prism/ folder-based storage instead.
    """
    pass

cli.add_command(strat)
cli.add_command(exec)
cli.add_command(status)
cli.add_command(init)
cli.add_command(task)

if __name__ == '__main__':
    cli()