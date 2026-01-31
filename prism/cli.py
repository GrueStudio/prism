import click

from prism.commands.strat import strat
from prism.commands.exec import exec
from prism.commands.status import status

@click.group()
def cli():
    """A command-line interface for project management and task tracking."""
    pass

cli.add_command(strat)
cli.add_command(exec)
cli.add_command(status)

if __name__ == '__main__':
    cli()