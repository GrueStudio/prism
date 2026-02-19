import json
from pathlib import Path

import click

from prism.data_store_old import DataStore
from prism.models_old import ProjectData


@click.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force re-initialization, overwriting existing project.json.",
)
def init(force):
    """Initializes a new Prism project."""
    project_file = Path("project.json")
    if project_file.exists() and not force:
        click.confirm(
            f"A project file already exists at {project_file.resolve()}. Do you want to overwrite it?",
            abort=True,
        )

    # Create a default project structure
    default_project = ProjectData()

    # Use DataStore for consistent file handling
    data_store = DataStore(project_file)
    try:
        data_store.save_project_data(default_project)
        click.echo(f"Prism project initialized at {project_file.resolve()}")
    except Exception as e:
        click.echo(
            f"Error: Could not write to project file at {project_file.resolve()}: {e}",
            err=True,
        )
