"""
Task commands for new Prism CLI using .prism/ storage.

Commands for managing tasks (start, done, next).
"""
import click
from typing import Optional

from prism.core import PrismCore
from prism.models.base import ItemStatus


@click.group()
def task():
    """Commands for managing tasks.

    When completing tasks, parent deliverables and objectives are automatically
    marked complete when all their children are done.
    """
    pass


def _display_task_start(core: PrismCore, action, completed_action=None):
    """Helper to display task start information with deliverable context."""
    # Check if we moved to a new deliverable
    show_deliverable = True
    deliverable = core.project.get_item(action.parent_uuid)
    
    if completed_action:
        if completed_action.parent_uuid == action.parent_uuid:
            show_deliverable = False
            
    if show_deliverable and deliverable:
        click.secho("\n" + "=" * 40, fg="blue")
        click.secho(f"🚀 Deliverable: ", nl=False)
        click.secho(deliverable.name, fg="blue", bold=True)
        if deliverable.description:
            click.echo(f"   {deliverable.description}")
        click.secho("=" * 40 + "\n", fg="blue")

    status_indicator = "⏳ " if action.status == ItemStatus.IN_PROGRESS else ""
    click.secho(f"{status_indicator}Working on: ", nl=False)
    click.secho(action.name, fg="cyan", bold=True)
    if action.description:
        click.echo(f"   {action.description}")


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
        _display_task_start(core, action)
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
        click.secho("✓ ", fg="green", nl=False)
        click.echo("Completed task: ", nl=False)
        click.secho(action.name, fg="green", bold=True)
    else:
        click.secho("No task in progress.", fg="yellow")


@task.command()
def pause():
    """Mark the current task as paused."""
    core = PrismCore()
    action = core.task_manager.pause_current_action()
    if action:
        click.secho("⏸ ", fg="yellow", nl=False)
        click.echo("Paused task: ", nl=False)
        click.secho(action.name, fg="yellow", bold=True)
    else:
        click.secho("No task in progress to pause.", fg="yellow")


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
        click.secho("✓ ", fg="green", nl=False)
        click.echo("Completed task: ", nl=False)
        click.secho(completed.name, fg="green", bold=True)
        if next_action:
            _display_task_start(core, next_action, completed_action=completed)
        else:
            click.secho("\n🎉 All tasks completed!", fg="magenta", bold=True)
    else:
        click.secho("No task in progress to complete.", fg="yellow")
