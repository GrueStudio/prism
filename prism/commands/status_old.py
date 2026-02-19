"""
DEPRECATED: Old status command using project.json storage.

This module is deprecated and will be removed in a future version.
Use prism/commands/status.py with .prism/ folder-based storage instead.
"""

import warnings

import click

warnings.warn(
    "Old status command (project.json storage) is deprecated. "
    "Use the new status command with .prism/ storage instead.",
    DeprecationWarning,
    stacklevel=2,
)

import json
from datetime import datetime

from prism.constants import STATUS_HEADER_WIDTH
from prism.core_old import Core


def display_exec_tree(
    core,
    objective,
    current_action_path=None,
    indent_level=0,
    current_deliverable_only=False,
):
    """Display the execution tree for an objective with completion indicators."""
    indent = "  " * indent_level

    current_deliverable = None
    if current_action_path:
        # Find the deliverable that contains the current action
        for deliverable in objective.deliverables:
            for action in deliverable.actions:
                action_path = core.navigator.get_item_path(action)
                if action_path == current_action_path:
                    current_deliverable = deliverable
                    break
            if current_deliverable:
                break

    # Determine which deliverables to display
    deliverables_to_display = objective.deliverables
    if current_deliverable_only and current_deliverable:
        deliverables_to_display = [current_deliverable]

    for deliverable in deliverables_to_display:
        # Calculate completion percentage for this deliverable
        deliv_completion = core.calculate_completion_percentage(deliverable)
        completion_text = (
            f" ({deliv_completion['overall']:.1f}%)"
            if deliv_completion["overall"] > 0
            else " (0%)"
        )

        # Check if any action in this deliverable is the current one
        current_indicator = ""
        for action in deliverable.actions:
            action_path = core.navigator.get_item_path(action)
            if action_path == current_action_path:
                current_indicator = " →"  # Current action indicator
                break

        # Determine status indicator
        status_indicator = ""
        if deliverable.status == "completed":
            status_indicator = " ✓"
        elif deliverable.status == "in-progress":
            status_indicator = " ⏳"

        click.echo(f"{indent}- {deliverable.name}{completion_text}{status_indicator}")

        # Display actions under this deliverable
        for action in deliverable.actions:
            action_path = core.navigator.get_item_path(action)
            action_indent = "  " + indent

            # Calculate action-specific indicators
            action_indicator = ""
            if action_path == current_action_path:
                action_indicator = " →"  # Current action indicator

            action_status_indicator = ""
            if action.status == "completed":
                action_status_indicator = " ✓"
            elif action.status == "in-progress":
                action_status_indicator = " ⏳"

            click.echo(
                f"{action_indent}- {action.name}{action_status_indicator}{action_indicator}"
            )


def get_exec_tree_data(
    core, objective, current_action_path=None, current_deliverable_only=False
):
    """Get execution tree data in a structured format for JSON output."""
    current_deliverable = None
    if current_action_path:
        # Find the deliverable that contains the current action
        for deliverable in objective.deliverables:
            for action in deliverable.actions:
                action_path = core.navigator.get_item_path(action)
                if action_path == current_action_path:
                    current_deliverable = deliverable
                    break
            if current_deliverable:
                break

    # Determine which deliverables to include
    deliverables_to_include = objective.deliverables
    if current_deliverable_only and current_deliverable:
        deliverables_to_include = [current_deliverable]

    tree_data = []
    for deliverable in deliverables_to_include:
        # Calculate completion percentage for this deliverable
        deliv_completion = core.calculate_completion_percentage(deliverable)

        deliverable_data = {
            "name": deliverable.name,
            "slug": deliverable.slug,
            "status": deliverable.status,
            "completion_percentage": deliv_completion["overall"],
            "actions": [],
        }

        for action in deliverable.actions:
            action_path = core.navigator.get_item_path(action)
            action_data = {
                "name": action.name,
                "slug": action.slug,
                "status": action.status,
                "is_current": action_path == current_action_path,
            }
            deliverable_data["actions"].append(action_data)

        tree_data.append(deliverable_data)

    return tree_data


@click.command(name="status")
@click.option("--phase", "phase_path", help="Filter status by a specific phase path.")
@click.option(
    "--milestone", "milestone_path", help="Filter status by a specific milestone path."
)
@click.option(
    "--current-deliverable",
    "current_deliverable_only",
    is_flag=True,
    help="Show only the current deliverable (containing the current action).",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output status in JSON format for AI agents.",
)
def status(phase_path, milestone_path, current_deliverable_only, json_output):
    """Displays a summary of project progress."""
    core = Core()
    summary = core.get_status_summary(
        phase_path=phase_path, milestone_path=milestone_path
    )

    # Handle JSON output first
    if json_output:
        current_items = core.get_current_strategic_items()
        current_action = core.get_current_action()
        current_action_path = (
            core.navigator.get_item_path(current_action) if current_action else None
        )

        result = {
            "current_strategic_focus": {},
            "execution_tree": [],
            "overdue_actions": summary["overdue_actions"],
            "orphaned_items": summary["orphaned_items"],
        }

        if current_items["objective"]:
            result["current_strategic_focus"] = {
                "phase": {
                    "name": current_items["phase"].name
                    if current_items["phase"]
                    else None,
                    "status": current_items["phase"].status
                    if current_items["phase"]
                    else None,
                }
                if current_items["phase"]
                else None,
                "milestone": {
                    "name": current_items["milestone"].name
                    if current_items["milestone"]
                    else None,
                    "status": current_items["milestone"].status
                    if current_items["milestone"]
                    else None,
                }
                if current_items["milestone"]
                else None,
                "objective": {
                    "name": current_items["objective"].name
                    if current_items["objective"]
                    else None,
                    "status": current_items["objective"].status
                    if current_items["objective"]
                    else None,
                }
                if current_items["objective"]
                else None,
            }

            if current_items["objective"]:
                result["execution_tree"] = get_exec_tree_data(
                    core,
                    current_items["objective"],
                    current_action_path,
                    current_deliverable_only,
                )

        click.echo(json.dumps(result, indent=2))
        return

    # Regular text output
    title = "Project Status Summary"
    if phase_path:
        title += f" for Phase '{phase_path}'"
    elif milestone_path:
        title += f" for Milestone '{milestone_path}'"

    click.echo(click.style(title, bold=True, fg="cyan"))
    click.echo(
        "=" * (len(title) if len(title) > STATUS_HEADER_WIDTH else STATUS_HEADER_WIDTH)
    )

    # Show current strategic items if not filtered by phase or milestone
    if not phase_path and not milestone_path:
        current_items = core.get_current_strategic_items()
        if current_items["objective"]:
            click.echo(click.style("\nCurrent Strategic Focus:", bold=True))
            if current_items["phase"]:
                phase_status = (
                    f" ({current_items['phase'].status})"
                    if current_items["phase"].status != "pending"
                    else ""
                )
                click.echo(f"- Phase: {current_items['phase'].name}{phase_status}")
            if current_items["milestone"]:
                milestone_status = (
                    f" ({current_items['milestone'].status})"
                    if current_items["milestone"].status != "pending"
                    else ""
                )
                click.echo(
                    f"- Milestone: {current_items['milestone'].name}{milestone_status}"
                )
            if current_items["objective"]:
                objective_status = (
                    f" ({current_items['objective'].status})"
                    if current_items["objective"].status != "pending"
                    else ""
                )
                # Calculate and show completion percentage for the current objective
                obj_completion = core.calculate_completion_percentage(
                    current_items["objective"]
                )
                completion_text = (
                    f" - {obj_completion['overall']:.1f}% complete"
                    if obj_completion["overall"] > 0
                    else ""
                )
                click.echo(
                    f"- Objective: {current_items['objective'].name}{objective_status}{completion_text}"
                )

                # Show the execution tree for the current objective
                current_action = core.get_current_action()
                current_action_path = (
                    core.navigator.get_item_path(current_action)
                    if current_action
                    else None
                )

                section_title = (
                    "\nCurrent Deliverable:"
                    if current_deliverable_only
                    else "\nExecution Tree:"
                )
                click.echo(click.style(section_title, bold=True))
                display_exec_tree(
                    core,
                    current_items["objective"],
                    current_action_path,
                    indent_level=1,
                    current_deliverable_only=current_deliverable_only,
                )

    if summary["overdue_actions"]:
        click.echo(click.style("\nOverdue Actions:", bold=True, fg="red"))
        for action in summary["overdue_actions"]:
            due_date = datetime.fromisoformat(action["due_date"]).strftime("%Y-%m-%d")
            click.echo(f"- Path: {action['path']} (Due: {due_date})")
    else:
        click.echo(click.style("\nNo overdue actions.", fg="green"))

    if summary["orphaned_items"]:
        click.echo(click.style("\nOrphaned Items:", bold=True, fg="yellow"))
        click.echo("(Items whose parent is completed, but they are not)")
        for item in summary["orphaned_items"]:
            click.echo(f"- Path: {item['path']} (Type: {item['type']})")
    else:
        click.echo(click.style("\nNo orphaned items found.", fg="green"))

    click.echo("\n" + "=" * (len(title) if len(title) > 25 else 25))
