"""
CompletionTracker for cascade completion and percentage calculations.

Handles completion cascading and progress tracking.
"""

from typing import Dict

import click

from prism.constants import PERCENTAGE_ROUND_PRECISION
from prism.managers.events import EventType, ItemEvent, publish_event
from prism.managers.navigation_manager import NavigationManager
from prism.models.base import Action, BaseItem, Deliverable, Objective


class CompletionTracker:
    """
    Tracks completion status and calculates progress percentages.

    Handles:
    - Cascading completion up the hierarchy
    - Calculating completion percentages for objectives and deliverables
    - Checking if execution trees are complete
    - Emitting events on strategic item completion
    """

    def __init__(
        self,
        navigator: NavigationManager,
        round_precision: int = None,
        emit_events: bool = True,
    ) -> None:
        """
        Initialize CompletionTracker.

        Args:
            navigator: NavigationManager instance for path resolution.
            round_precision: Decimal places for percentage rounding. Defaults to config value.
            emit_events: Whether to emit completion events.
        """
        self.navigator = navigator
        self._round_precision = round_precision or PERCENTAGE_ROUND_PRECISION
        self._emit_events = emit_events

    def cascade_completion(self, item: BaseItem) -> None:
        """Cascade completion status up the tree when all children are complete.

        When all actions in a deliverable are complete, mark deliverable complete.
        When all deliverables in an objective are complete, mark objective complete.

        Does NOT cascade to milestones or phases to allow adding new children.

        Prints a notification when a parent item is marked complete.
        Emits STRATEGIC_COMPLETED event for objectives.

        Args:
            item: The completed item.
        """
        from datetime import datetime

        # Get the parent of the completed item
        item_path = self.navigator.get_item_path(item)
        if not item_path:
            return

        segments = item_path.split("/")
        if len(segments) < 2:
            return  # Top-level item, no parent to update

        parent_path = "/".join(segments[:-1])
        parent = self.navigator.get_item_by_path(parent_path)
        if not parent:
            return

        # Check if all children are complete and update parent status
        all_children_complete = False

        if isinstance(item, Action) and isinstance(parent, Deliverable):
            # Check if all actions in deliverable are complete
            if parent.actions:
                all_children_complete = all(
                    a.status == "completed" for a in parent.actions
                )
        elif isinstance(item, Deliverable) and isinstance(parent, Objective):
            # Check if all deliverables in objective are complete
            if parent.deliverables:
                all_children_complete = all(
                    d.status == "completed" for d in parent.deliverables
                )

        # If all children are complete, mark parent as complete and continue cascading
        # Only cascade up to objective level (not milestones or phases)
        if all_children_complete and parent.status != "completed":
            parent.status = "completed"
            parent.updated_at = datetime.now()
            click.echo(f"  ✓ {type(parent).__name__} '{parent.name}' marked complete")

            # Emit event for strategic item completion
            if self._emit_events and isinstance(parent, Objective):
                self._emit_strategic_completed(parent)

            # Continue cascading only if parent is a deliverable (cascade to objective)
            if isinstance(parent, Deliverable):
                self.cascade_completion(parent)

    def _emit_strategic_completed(self, objective: Objective) -> None:
        """Emit STRATEGIC_COMPLETED event for an objective.

        Args:
            objective: The completed objective.
        """
        event = ItemEvent(
            type=EventType.STRATEGIC_COMPLETED,
            item_uuid=objective.uuid,
            item_type="objective",
            item_slug=objective.slug,
            item_name=objective.name,
            status=objective.status,
            parent_uuid=objective.parent_uuid,
        )
        publish_event(event)

    def calculate_completion_percentage(self, item: BaseItem) -> Dict[str, float]:
        """Calculate completion percentage for objectives and deliverables.

        Args:
            item: Item to calculate percentage for.

        Returns:
            Dictionary with 'overall' percentage and 'by_type' breakdown.
        """
        if isinstance(item, Objective):
            if len(item.deliverables) == 0:
                return {"overall": 0.0, "by_type": {"deliverables": 0.0}}

            completed_deliverables = sum(
                1 for d in item.deliverables if d.status == "completed"
            )
            total_deliverables = len(item.deliverables)

            # Calculate completion for each deliverable's actions
            total_actions = 0
            completed_actions = 0

            for deliverable in item.deliverables:
                for action in deliverable.actions:
                    total_actions += 1
                    if action.status == "completed":
                        completed_actions += 1

            return {
                "overall": round(
                    (completed_deliverables / total_deliverables) * 100,
                    self._round_precision,
                )
                if total_deliverables > 0
                else 0.0,
                "by_type": {
                    "deliverables": round(
                        (completed_deliverables / total_deliverables) * 100,
                        self._round_precision,
                    )
                    if total_deliverables > 0
                    else 0.0,
                    "actions": round(
                        (completed_actions / total_actions) * 100,
                        self._round_precision,
                    )
                    if total_actions > 0
                    else 0.0,
                },
            }

        elif isinstance(item, Deliverable):
            if len(item.actions) == 0:
                return {"overall": 0.0}

            completed_actions = sum(1 for a in item.actions if a.status == "completed")
            total_actions = len(item.actions)

            return {
                "overall": round(
                    (completed_actions / total_actions) * 100, self._round_precision
                ),
                "by_type": {
                    "actions": round(
                        (completed_actions / total_actions) * 100, self._round_precision
                    )
                },
            }

        return {"overall": 0.0}

    def is_exec_tree_complete(self, objective: Objective) -> bool:
        """Check if an execution tree (deliverables and actions) is complete.

        Args:
            objective: Objective to check.

        Returns:
            True if all deliverables and actions are complete.
        """
        if not objective.deliverables:
            return False

        for deliverable in objective.deliverables:
            if deliverable.status != "completed":
                return False
            for action in deliverable.actions:
                if action.status != "completed":
                    return False

        return True

    def get_completion_stats(self, item: BaseItem) -> Dict[str, int]:
        """Get completion statistics for an item.

        Args:
            item: Item to get stats for.

        Returns:
            Dictionary with total, completed, and pending counts.
        """
        if isinstance(item, Objective):
            total_del = len(item.deliverables)
            completed_del = sum(1 for d in item.deliverables if d.status == "completed")
            total_act = sum(len(d.actions) for d in item.deliverables)
            completed_act = sum(
                sum(1 for a in d.actions if a.status == "completed")
                for d in item.deliverables
            )
            return {
                "deliverables_total": total_del,
                "deliverables_completed": completed_del,
                "deliverables_pending": total_del - completed_del,
                "actions_total": total_act,
                "actions_completed": completed_act,
                "actions_pending": total_act - completed_act,
            }
        elif isinstance(item, Deliverable):
            total = len(item.actions)
            completed = sum(1 for a in item.actions if a.status == "completed")
            return {
                "actions_total": total,
                "actions_completed": completed,
                "actions_pending": total - completed,
            }
        return {}
