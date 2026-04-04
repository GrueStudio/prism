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


def _display_status_changes(events):
    """Display status change events to the user."""
    for event in events:
        if not event.cascaded:
            continue
            
        icon = "✓" if event.new_status == ItemStatus.COMPLETED else "→"
        if event.new_status == ItemStatus.PAUSED:
            icon = "⏸"
            
        color = "green" if event.new_status == ItemStatus.COMPLETED else "blue"
        if event.new_status == ItemStatus.PAUSED:
            color = "yellow"
            
        click.secho(f"  {icon} ", fg=color, nl=False)
        click.echo(f"{type(event.item).__name__} '", nl=False)
        click.secho(event.item.name, bold=True, nl=False)
        click.echo(f"' marked {event.new_status.value}")


def _display_task_start(
    core: PrismCore, action, completed_action=None, events=None, is_resume=False
):
    """Helper to display task start information with deliverable context."""
    if events:
        _display_status_changes(events)

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

    if is_resume:
        click.secho("▶️  Resuming task: ", fg="cyan", nl=False)
    else:
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

    # Check if we're about to resume a paused task
    current = core.task_manager.get_current_action()
    was_paused = current and current.status == ItemStatus.PAUSED and not path

    action, events = core.task_manager.start_next_action(path=path)
    if action:
        _display_task_start(core, action, events=events, is_resume=was_paused)
    else:
        click.echo("No pending tasks found.")


@task.command()
def done():
    """Mark the current task as done.

    If all actions in a deliverable are complete, the deliverable is marked done.
    If all deliverables in an objective are complete, the objective is marked done.
    """
    core = PrismCore()

    # Check status before completing for better feedback
    current = core.task_manager.get_current_action()
    if current and current.status == ItemStatus.PAUSED:
        click.secho("⏸  Task is currently paused: ", fg="yellow", nl=False)
        click.secho(current.name, fg="yellow", bold=True)
        click.echo("Please resume it with 'prism task start' before completing.")
        return

    action, events = core.task_manager.complete_current_action()
    if action:
        click.secho("✓ ", fg="green", nl=False)
        click.echo("Completed task: ", nl=False)
        click.secho(action.name, fg="green", bold=True)
        _display_status_changes(events)
    else:
        click.secho("No task in progress.", fg="yellow")


@task.command()
def pause():
    """Mark the current task as paused."""
    core = PrismCore()
    action, events = core.task_manager.pause_current_action()
    if action:
        click.secho("⏸ ", fg="yellow", nl=False)
        click.echo("Paused task: ", nl=False)
        click.secho(action.name, fg="yellow", bold=True)
        _display_status_changes(events)
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
    completed, next_action, events = core.task_manager.complete_current_and_start_next(
        next_path=path, reset=reset
    )
    if completed:
        click.secho("✓ ", fg="green", nl=False)
        click.echo("Completed task: ", nl=False)
        click.secho(completed.name, fg="green", bold=True)
        if next_action:
            _display_task_start(core, next_action, completed_action=completed, events=events)
        else:
            _display_status_changes(events)
            click.secho("\n🎉 All tasks completed!", fg="magenta", bold=True)
    else:
        click.secho("No task in progress to complete.", fg="yellow")
