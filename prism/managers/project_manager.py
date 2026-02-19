"""
ProjectManager for building and managing project structure.

Builds hierarchical structure from flat storage on demand.
Uses ArchivedItem wrappers for lazy-loading archived items.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from prism.models.strategic import Phase, Milestone, Objective
from prism.models.execution import Deliverable, Action
from prism.managers.storage_manager import StorageManager
from prism.models import StrategicFile, ExecutionFile
from prism.archived_item import ArchivedItem


@dataclass
class Project:
    """
    In-memory project data with hierarchical structure.

    Built from flat storage on load.
    Flattened back to storage on save.
    
    Archived items are represented as ArchivedItem wrappers for lazy loading.
    """
    phases: List[Union[Phase, ArchivedItem]] = field(default_factory=list)
    cursor: Optional[str] = None

    # Lookup maps for fast access (includes both real and archived items)
    _phase_map: Dict[str, Union[Phase, ArchivedItem]] = field(default_factory=dict)
    _milestone_map: Dict[str, Union[Milestone, ArchivedItem]] = field(default_factory=dict)
    _objective_map: Dict[str, Union[Objective, ArchivedItem]] = field(default_factory=dict)
    _deliverable_map: Dict[str, Union[Deliverable, ArchivedItem]] = field(default_factory=dict)
    _action_map: Dict[str, Union[Action, ArchivedItem]] = field(default_factory=dict)

    def build_maps(self) -> None:
        """Build lookup maps from hierarchical structure."""
        self._phase_map.clear()
        self._milestone_map.clear()
        self._objective_map.clear()
        self._deliverable_map.clear()
        self._action_map.clear()

        for phase in self.phases:
            self._phase_map[phase.uuid] = phase
            # Handle both Phase objects and ArchivedItem wrappers
            milestones = phase.milestones if isinstance(phase, Phase) else phase.children
            for milestone in milestones:
                self._milestone_map[milestone.uuid] = milestone
                # Handle both Milestone objects and ArchivedItem wrappers
                objectives = milestone.objectives if isinstance(milestone, Milestone) else milestone.children
                for objective in objectives:
                    self._objective_map[objective.uuid] = objective
                    # Handle both Objective objects and ArchivedItem wrappers
                    deliverables = objective.deliverables if isinstance(objective, Objective) else objective.get_deliverables()
                    for deliverable in deliverables:
                        self._deliverable_map[deliverable.uuid] = deliverable
                        # Handle both Deliverable objects and ArchivedItem wrappers
                        actions = deliverable.actions if isinstance(deliverable, Deliverable) else deliverable.get_actions()
                        for action in actions:
                            self._action_map[action.uuid] = action

    def get_by_uuid(self, uuid: str):
        """Get any item by UUID (real or archived)."""
        return (
            self._phase_map.get(uuid)
            or self._milestone_map.get(uuid)
            or self._objective_map.get(uuid)
            or self._deliverable_map.get(uuid)
            or self._action_map.get(uuid)
        )


class ProjectManager:
    """
    Manages project structure building and persistence.
    
    Builds hierarchical structure from flat storage.
    Flattens hierarchy back to storage on save.
    """
    
    def __init__(self, storage: StorageManager) -> None:
        """
        Initialize ProjectManager.
        
        Args:
            storage: StorageManager for persistence.
        """
        self.storage = storage
        self.project = Project()
    
    def load(self) -> Project:
        """
        Load project from storage and build hierarchical structure.

        Loads active items as full objects.
        Loads archived items as ArchivedItem wrappers for lazy loading.

        Returns:
            Project with hierarchical structure.
        """
        strategic = self.storage.load_strategic()
        execution = self.storage.load_execution()

        self.project = Project()

        # Build active items first
        all_items: Dict[str, object] = {}

        # Load active phase
        if strategic.phase:
            phase = Phase(
                uuid=strategic.phase['uuid'],
                name=strategic.phase['name'],
                description=strategic.phase.get('description'),
                slug=strategic.phase['slug'],
                status=strategic.phase.get('status', 'pending'),
                parent_uuid=None,
            )
            all_items[phase.uuid] = phase
            self.project.phases.append(phase)

        # Load active milestone
        if strategic.milestone:
            milestone = Milestone(
                uuid=strategic.milestone['uuid'],
                name=strategic.milestone['name'],
                description=strategic.milestone.get('description'),
                slug=strategic.milestone['slug'],
                status=strategic.milestone.get('status', 'pending'),
                parent_uuid=strategic.milestone.get('parent_uuid'),
            )
            all_items[milestone.uuid] = milestone
            # Add to parent phase
            if milestone.parent_uuid and milestone.parent_uuid in all_items:
                parent = all_items[milestone.parent_uuid]
                if isinstance(parent, Phase):
                    parent.milestones.append(milestone)

        # Load active objective
        if strategic.objective:
            objective = Objective(
                uuid=strategic.objective['uuid'],
                name=strategic.objective['name'],
                description=strategic.objective.get('description'),
                slug=strategic.objective['slug'],
                status=strategic.objective.get('status', 'pending'),
                parent_uuid=strategic.objective.get('parent_uuid'),
            )
            all_items[objective.uuid] = objective
            # Add to parent milestone
            if objective.parent_uuid and objective.parent_uuid in all_items:
                parent = all_items[objective.parent_uuid]
                if isinstance(parent, Milestone):
                    parent.objectives.append(objective)

        # Load active execution items
        for del_data in execution.deliverables:
            deliverable = Deliverable(
                uuid=del_data['uuid'],
                name=del_data['name'],
                description=del_data.get('description'),
                slug=del_data['slug'],
                status=del_data.get('status', 'pending'),
                parent_uuid=del_data.get('parent_uuid'),
            )
            all_items[deliverable.uuid] = deliverable
            if deliverable.parent_uuid and deliverable.parent_uuid in all_items:
                parent = all_items[deliverable.parent_uuid]
                if isinstance(parent, Objective):
                    parent.deliverables.append(deliverable)

        for act_data in execution.actions:
            action = Action(
                uuid=act_data['uuid'],
                name=act_data['name'],
                description=act_data.get('description'),
                slug=act_data['slug'],
                status=act_data.get('status', 'pending'),
                parent_uuid=act_data.get('parent_uuid'),
                due_date=act_data.get('due_date'),
                time_spent=act_data.get('time_spent'),
            )
            all_items[action.uuid] = action
            if action.parent_uuid and action.parent_uuid in all_items:
                parent = all_items[action.parent_uuid]
                if isinstance(parent, Deliverable):
                    parent.actions.append(action)

        # Load archived items as ArchivedItem wrappers
        archived = self.storage.load_all_archived_strategic()
        
        # Create archived phase wrappers
        for phase_data in archived['phases']:
            archived_phase = ArchivedItem(
                uuid=phase_data['uuid'],
                name=phase_data['name'],
                slug=phase_data['slug'],
                item_type='phase',
                status=phase_data.get('status', 'archived'),
                parent_uuid=None,
                description=phase_data.get('description'),
                storage=self.storage,
            )
            all_items[archived_phase.uuid] = archived_phase
            self.project.phases.append(archived_phase)
        
        # Create archived milestone wrappers and add to parent phases
        for milestone_data in archived['milestones']:
            archived_milestone = ArchivedItem(
                uuid=milestone_data['uuid'],
                name=milestone_data['name'],
                slug=milestone_data['slug'],
                item_type='milestone',
                status=milestone_data.get('status', 'archived'),
                parent_uuid=milestone_data.get('parent_uuid'),
                description=milestone_data.get('description'),
                storage=self.storage,
            )
            all_items[archived_milestone.uuid] = archived_milestone
            # Add to parent phase (real or archived)
            if archived_milestone.parent_uuid and archived_milestone.parent_uuid in all_items:
                parent = all_items[archived_milestone.parent_uuid]
                if isinstance(parent, Phase):
                    parent.milestones.append(archived_milestone)
                elif isinstance(parent, ArchivedItem) and parent.item_type == 'phase':
                    # For archived phases, we need to use a different approach
                    # since ArchivedItem doesn't have a milestones attribute
                    pass  # Will be accessible via parent.children
        
        # Create archived objective wrappers and add to parent milestones
        for objective_data in archived['objectives']:
            archived_objective = ArchivedItem(
                uuid=objective_data['uuid'],
                name=objective_data['name'],
                slug=objective_data['slug'],
                item_type='objective',
                status=objective_data.get('status', 'archived'),
                parent_uuid=objective_data.get('parent_uuid'),
                description=objective_data.get('description'),
                storage=self.storage,
            )
            all_items[archived_objective.uuid] = archived_objective
            # Add to parent milestone (real or archived)
            if archived_objective.parent_uuid and archived_objective.parent_uuid in all_items:
                parent = all_items[archived_objective.parent_uuid]
                if isinstance(parent, Milestone):
                    parent.objectives.append(archived_objective)
                elif isinstance(parent, ArchivedItem) and parent.item_type == 'milestone':
                    pass  # Will be accessible via parent.children

        self.project.build_maps()
        self.project.cursor = None  # TODO: Load cursor from dedicated cursor file or config
        return self.project
    
    def save(self, project: Project) -> None:
        """
        Save project to storage by flattening hierarchy.
        
        Args:
            project: Project with hierarchical structure.
        """
        strategic_items = []
        execution_deliverables = []
        execution_actions = []
        
        def traverse_phase(phase: Phase, parent_uuid: Optional[str] = None) -> None:
            strategic_items.append({
                'uuid': phase.uuid,
                'type': 'phase',
                'name': phase.name,
                'description': phase.description,
                'slug': phase.slug,
                'status': phase.status,
                'parent_uuid': parent_uuid,
            })
            for milestone in phase.milestones:
                traverse_milestone(milestone, phase.uuid)
        
        def traverse_milestone(milestone: Milestone, parent_uuid: str) -> None:
            strategic_items.append({
                'uuid': milestone.uuid,
                'type': 'milestone',
                'name': milestone.name,
                'description': milestone.description,
                'slug': milestone.slug,
                'status': milestone.status,
                'parent_uuid': parent_uuid,
            })
            for objective in milestone.objectives:
                traverse_objective(objective, milestone.uuid)
        
        def traverse_objective(objective: Objective, parent_uuid: str) -> None:
            strategic_items.append({
                'uuid': objective.uuid,
                'type': 'objective',
                'name': objective.name,
                'description': objective.description,
                'slug': objective.slug,
                'status': objective.status,
                'parent_uuid': parent_uuid,
            })
            for deliverable in objective.deliverables:
                traverse_deliverable(deliverable, objective.uuid)
        
        def traverse_deliverable(deliverable: Deliverable, parent_uuid: str) -> None:
            execution_deliverables.append({
                'uuid': deliverable.uuid,
                'name': deliverable.name,
                'description': deliverable.description,
                'slug': deliverable.slug,
                'status': deliverable.status,
                'parent_uuid': parent_uuid,
            })
            for action in deliverable.actions:
                traverse_action(action, deliverable.uuid)
        
        def traverse_action(action: Action, parent_uuid: str) -> None:
            execution_actions.append({
                'uuid': action.uuid,
                'name': action.name,
                'description': action.description,
                'slug': action.slug,
                'status': action.status,
                'parent_uuid': parent_uuid,
                'due_date': action.due_date.isoformat() if action.due_date else None,
                'time_spent': action.time_spent,
            })
        
        # Traverse all phases
        for phase in project.phases:
            traverse_phase(phase)
        
        # Save to storage
        self.storage.save_strategic(StrategicFile(items=strategic_items))
        self.storage.save_execution(ExecutionFile(
            deliverables=execution_deliverables,
            actions=execution_actions,
        ))
