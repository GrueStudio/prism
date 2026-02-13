import click
from pathlib import Path
import json

from prism.models import ProjectData

@click.command()
@click.option('--force', is_flag=True, help="Force re-initialization, overwriting existing project.json.")
def init(force):
    """Initializes a new Prism project."""
    project_file = Path("project.json")
    if project_file.exists() and not force:
        click.confirm(f"A project file already exists at {project_file.resolve()}. Do you want to overwrite it?", abort=True)

    # Create a default project structure
    default_project = ProjectData()

    try:
        with open(project_file, 'w') as f:
            f.write(default_project.model_dump_json(indent=2))
        click.echo(f"Prism project initialized at {project_file.resolve()}")
    except IOError as e:
        click.echo(f"Error: Could not write to project file at {project_file.resolve()}: {e}", err=True)

