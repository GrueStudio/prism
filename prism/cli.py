import click

from prism.commands.strat import strat
from prism.commands.exec import exec

@click.group()
def cli():
    """A command-line interface for project management and task tracking."""
    pass

cli.add_command(strat)
cli.add_command(exec)

if __name__ == '__main__':
    cli()