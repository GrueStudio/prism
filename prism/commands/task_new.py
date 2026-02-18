"""
Task commands for new Prism CLI using .prism/ storage.

Commands for managing tasks (start, done, next).
"""
import click

from prism.newcore import NewPrismCore


@click.group()
def task():
    """Commands for managing tasks.

    When completing tasks, parent deliverables and objectives are automatically
    marked complete when all their children are done.
    """
    pass


@task.command()
def start():
    """Start the next pending task, or show current in-progress task."""
    core = NewPrismCore()
    action = core.task_manager.start_next_action()
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
    core = NewPrismCore()
    action = core.task_manager.complete_current_action()
    if action:
        click.echo(f"Completed task: {action.name}")
    else:
        click.echo("No task in progress.")


@task.command()
def next():
    """Complete the current task and start the next one.

    If all actions in a deliverable are complete, the deliverable is marked done.
    If all deliverables in an objective are complete, the objective is marked done.
    """
    core = NewPrismCore()
    completed, next_action = core.task_manager.complete_current_and_start_next()
    if completed:
        click.echo(f"Completed task: {completed.name}")
        if next_action:
            click.echo(f"Started next task: {next_action.name}")
        else:
            click.echo("All tasks completed!")
    else:
        click.echo("No task in progress to complete.")
