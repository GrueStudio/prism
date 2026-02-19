"""
DEPRECATED: Old task commands using project.json storage.

This module is deprecated and will be removed in a future version.
Use prism/commands/task.py with .prism/ folder-based storage instead.
"""
import click
import warnings

warnings.warn(
    "Old task commands (project.json storage) are deprecated. "
    "Use the new task commands with .prism/ storage instead.",
    DeprecationWarning,
    stacklevel=2
)

from prism.core import Core

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
    core = Core()
    action = core.start_next_action()
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
    core = Core()
    action = core.complete_current_action()
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
