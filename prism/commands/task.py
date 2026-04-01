"""
Task commands for new Prism CLI using .prism/ storage.

Commands for managing tasks (start, done, next).
"""
import click
from typing import Optional

from prism.core import PrismCore


@click.group()
def task():
    """Commands for managing tasks.

    When completing tasks, parent deliverables and objectives are automatically
    marked complete when all their children are done.
    """
    pass


@task.command()
@click.argument("path", required=False)
def start(path: Optional[str]):
    """Start the next pending task, or show current in-progress task.

    If PATH is provided, start a specific action or the first pending action
    of a deliverable.
    """
    core = PrismCore()
    action = core.task_manager.start_next_action(path=path)
    if action:
        click.echo(f"Currently working on: {action.name}")
    else:
        click.echo("No pending tasks found.")


@task.command()
def done():
    """Mark the current task as done.

    If all actions in a deliverable are complete, the deliverable is marked done.
    If all deliverables in an objective are complete, the objective is marked done.
    """
    core = PrismCore()
    action = core.task_manager.complete_current_action()
    if action:
        click.echo(f"Completed task: {action.name}")
    else:
        click.echo("No task in progress.")


@task.command()
@click.argument("path", required=False)
@click.option("--reset", is_flag=True, help="Reset to first action of current deliverable.")
def next(path: Optional[str], reset: bool):
    """Complete the current task and start the next one.

    If PATH is provided, start that specific task next.
    If --reset is used, start the first task of the current deliverable.

    If all actions in a deliverable are complete, the deliverable is marked done.
    If all deliverables in an objective are complete, the objective is marked done.
    """
    core = PrismCore()
    completed, next_action = core.task_manager.complete_current_and_start_next(
        next_path=path, reset=reset
    )
    if completed:
        click.echo(f"Completed task: {completed.name}")
        if next_action:
            click.echo(f"Started next task: {next_action.name}")
        else:
            click.echo("All tasks completed!")
    else:
        click.echo("No task in progress to complete.")
