import click

from prism.core import Core

@click.group()
def task():
    """Commands for managing tasks."""
    pass

@task.command()
def start():
    """Start the next pending task, or show current in-progress task."""
    core = Core()
    action = core.start_next_action()
    if action:
        click.echo(f"Currently working on: {action.name}")
    else:
        click.echo("No pending tasks found.")

@task.command()
def done():
    """Mark the current task as done."""
    core = Core()
    action = core.complete_current_action()
    if action:
        click.echo(f"Completed task: {action.name}")
    else:
        click.echo("No task in progress.")

@task.command()
def next():
    """Complete the current task and start the next one."""
    core = Core()
    completed_action, next_action = core.complete_current_and_start_next()
    if completed_action:
        click.echo(f"Completed task: {completed_action.name}")
        if next_action:
            click.echo(f"Started next task: {next_action.name}")
        else:
            click.echo("All tasks completed!")
    else:
        click.echo("No task in progress to complete.")
