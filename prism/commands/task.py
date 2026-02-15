import click

from prism.tracker import Tracker

@click.group()
def task():
    """Commands for managing tasks."""
    pass

@task.command()
def start():
    """Start the next pending task, or show current in-progress task."""
    tracker = Tracker()
    action = tracker.start_next_action()
    if action:
        if action.status == "in-progress":
            click.echo(f"Currently working on: {action.name}")
        else: # Should not happen with new logic, but good for safety
            click.echo(f"Started task: {action.name}")
    else:
        click.echo("No pending tasks found.")

@task.command()
def done():
    """Mark the current task as done."""
    tracker = Tracker()
    action = tracker.complete_current_action()
    if action:
        click.echo(f"Completed task: {action.name}")
        next_action = tracker.get_current_action()
        if next_action:
            click.echo(f"Next task: {next_action.name}")
        else:
            click.echo("All tasks completed!")
    else:
        click.echo("No task in progress.")

@task.command()
def next():
    """Complete the current task and start the next one."""
    tracker = Tracker()
    completed_action = tracker.complete_current_action()
    if completed_action:
        click.echo(f"Completed task: {completed_action.name}")
        next_action = tracker.get_current_action()
        if next_action:
            click.echo(f"Started next task: {next_action.name}")
        else:
            click.echo("All tasks completed!")
    else:
        click.echo("No task in progress to complete.")
