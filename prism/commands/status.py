"""
Status command for new Prism CLI using .prism/ storage.

Displays a summary of project progress.
"""

import json

import click

from prism.constants import STATUS_HEADER_WIDTH
from prism.core import PrismCore


def display_exec_tree(
    core, objective, current_action=None, current_deliverable_only=False
):
    """Display the execution tree for an objective with completion indicators."""
    current_deliverable = None
    if current_action:
        # Find the deliverable that contains the current action
        for deliverable in objective.children:
            if any(a.uuid == current_action.uuid for a in deliverable.children):
                current_deliverable = deliverable
                break

    # Determine which deliverables to display
    deliverables_to_display = objective.children
    if current_deliverable_only and current_deliverable:
        deliverables_to_display = [current_deliverable]

    for deliverable in deliverables_to_display:
        # Calculate completion percentage for this deliverable
        total_actions = len(deliverable.children)
        completed_actions = sum(
            1 for a in deliverable.children if a.status == "completed"
        )
        deliv_completion = (
            (completed_actions / total_actions * 100) if total_actions > 0 else 0
        )
        completion_text = (
            f" ({deliv_completion:.1f}%)" if deliv_completion > 0 else " (0%)"
        )

        # Check if any action in this deliverable is the current one
        current_indicator = ""
        if current_deliverable and deliverable.uuid == current_deliverable.uuid:
            current_indicator = " →"

        # Determine status indicator
        status_indicator = ""
        if deliverable.status == "completed":
            status_indicator = " ✓"
        elif deliverable.status == "in-progress":
            status_indicator = " ⏳"

        click.echo(f"- {deliverable.name}{completion_text}{status_indicator}")

        # Display actions under this deliverable
        for action in deliverable.children:
            action_indicator = (
                " →" if current_action and action.uuid == current_action.uuid else ""
            )
            action_status_indicator = ""
            if action.status == "completed":
                action_status_indicator = " ✓"
            elif action.status == "in-progress":
                action_status_indicator = " ⏳"

            click.echo(f"  - {action.name}{action_status_indicator}{action_indicator}")


def get_exec_tree_data(
    core, objective, current_action=None, current_deliverable_only=False
):
    """Get execution tree data in a structured format for JSON output."""
    current_deliverable = None
    if current_action:
        for deliverable in objective.children:
            if any(a.uuid == current_action.uuid for a in deliverable.children):
                current_deliverable = deliverable
                break

    deliverables_to_include = objective.children
    if current_deliverable_only and current_deliverable:
        deliverables_to_include = [current_deliverable]

    tree_data = []
    for deliverable in deliverables_to_include:
        total_actions = len(deliverable.children)
        completed_actions = sum(
            1 for a in deliverable.children if a.status == "completed"
        )
        deliv_completion = (
            (completed_actions / total_actions * 100) if total_actions > 0 else 0
        )

        deliverable_data = {
            "name": deliverable.name,
            "slug": deliverable.slug,
            "status": deliverable.status,
            "completion_percentage": round(deliv_completion, 1),
            "actions": [],
        }

        for action in deliverable.children:
            action_data = {
                "name": action.name,
                "slug": action.slug,
                "status": action.status,
                "is_current": current_action and action.uuid == current_action.uuid,
            }
            deliverable_data["actions"].append(action_data)

        tree_data.append(deliverable_data)

    return tree_data


@click.command(name="status")
@click.option(
    "--current-deliverable",
    "current_deliverable_only",
    is_flag=True,
    help="Show only the current deliverable (containing the current action).",
)
@click.option(
    "-j",
    "--json",
    "json_output",
    is_flag=True,
    help="Output status in JSON format for AI agents.",
)
def status(current_deliverable_only, json_output):
    """Displays a summary of project progress."""
    core = PrismCore()

    current_action = core.task_manager.get_current_action()
    current_objective = core.navigator.get_current_objective()
    current_milestone = core.navigator.get_current_milestone()
    current_phase = core.navigator.get_current_phase()

    # Handle JSON output first
    if json_output:
        result = {
            "current_strategic_focus": {},
            "execution_tree": [],
            "overdue_actions": [],
            "orphaned_items": [],
        }

        if current_objective:
            # Calculate objective completion
            total_delivs = len(current_objective.children)
            completed_delivs = sum(
                1 for d in current_objective.children if d.status == "completed"
            )
            obj_completion = (
                (completed_delivs / total_delivs * 100) if total_delivs > 0 else 0
            )

            result["current_strategic_focus"] = {
                "phase": {
                    "name": current_phase.name if current_phase else None,
                    "status": current_phase.status if current_phase else None,
                }
                if current_phase
                else None,
                "milestone": {
                    "name": current_milestone.name if current_milestone else None,
                    "status": current_milestone.status if current_milestone else None,
                }
                if current_milestone
                else None,
                "objective": {
                    "name": current_objective.name,
                    "status": current_objective.status,
                    "completion_percentage": round(obj_completion, 1),
                }
                if current_objective
                else None,
            }

            result["execution_tree"] = get_exec_tree_data(
                core, current_objective, current_action, current_deliverable_only
            )

        click.echo(json.dumps(result, indent=2))
        return

    # Regular text output
    click.echo("Project Status Summary")
    click.echo("=========================")
    click.echo()
    click.echo("Current Strategic Focus:")

    if current_phase:
        click.echo(f"- Phase: {current_phase.name}")
    if current_milestone:
        click.echo(f"- Milestone: {current_milestone.name}")
    if current_objective:
        # Calculate objective completion
        total_delivs = len(current_objective.children)
        completed_delivs = sum(
            1 for d in current_objective.children if d and d.status == "completed"
        )
        obj_completion = (
            (completed_delivs / total_delivs * 100) if total_delivs > 0 else 0
        )
        click.echo(
            f"- Objective: {current_objective.name} - {obj_completion:.1f}% complete"
        )
    click.echo()

    if current_objective:
        click.echo("Execution Tree:")
        display_exec_tree(
            core, current_objective, current_action, current_deliverable_only
        )
        click.echo()

    click.echo("No overdue actions.")
    click.echo()
    click.echo("No orphaned items found.")
    click.echo()
    click.echo("=========================")
