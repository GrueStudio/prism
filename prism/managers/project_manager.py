"""
ProjectManager for building and managing project structure.

Builds hierarchical structure from flat storage on demand.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from prism.models.strategic import Phase, Milestone, Objective
from prism.models.execution import Deliverable, Action
from prism.managers.storage_manager import StorageManager
from prism.models import StrategicFile, ExecutionFile


@dataclass
class Project:
    """
    In-memory project data with hierarchical structure.
    
    Built from flat storage on load.
    Flattened back to storage on save.
    """
    phases: List[Phase] = field(default_factory=list)
    cursor: Optional[str] = None
    
    # Lookup maps for fast access
    _phase_map: Dict[str, Phase] = field(default_factory=dict)
    _milestone_map: Dict[str, Milestone] = field(default_factory=dict)
    _objective_map: Dict[str, Objective] = field(default_factory=dict)
    _deliverable_map: Dict[str, Deliverable] = field(default_factory=dict)
    _action_map: Dict[str, Action] = field(default_factory=dict)
    
    def build_maps(self) -> None:
        """Build lookup maps from hierarchical structure."""
        self._phase_map.clear()
        self._milestone_map.clear()
        self._objective_map.clear()
        self._deliverable_map.clear()
        self._action_map.clear()
        
        for phase in self.phases:
            self._phase_map[phase.uuid] = phase
            for milestone in phase.milestones:
                self._milestone_map[milestone.uuid] = milestone
                for objective in milestone.objectives:
                    self._objective_map[objective.uuid] = objective
                    for deliverable in objective.deliverables:
                        self._deliverable_map[deliverable.uuid] = deliverable
                        for action in deliverable.actions:
                            self._action_map[action.uuid] = action
    
    def get_by_uuid(self, uuid: str):
        """Get any item by UUID."""
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

        Returns:
            Project with hierarchical structure.
        """
        strategic = self.storage.load_strategic()
        execution = self.storage.load_execution()

        self.project = Project()

        # Build lookup maps from flat data
        all_items: Dict[str, object] = {}

        # Load strategic items from new structure (phase, milestone, objective fields)
        strategic_items = []
        if strategic.phase:
            strategic_items.append(strategic.phase)
        if strategic.milestone:
            strategic_items.append(strategic.milestone)
        if strategic.objective:
            strategic_items.append(strategic.objective)

        for item_data in strategic_items:
            uuid = item_data['uuid']

            # Determine type by which field it came from
            if item_data == strategic.phase:
                item = Phase(
                    uuid=uuid,
                    name=item_data['name'],
                    description=item_data.get('description'),
                    slug=item_data['slug'],
                    status=item_data.get('status', 'pending'),
                    parent_uuid=item_data.get('parent_uuid'),
                )
            elif item_data == strategic.milestone:
                item = Milestone(
                    uuid=uuid,
                    name=item_data['name'],
                    description=item_data.get('description'),
                    slug=item_data['slug'],
                    status=item_data.get('status', 'pending'),
                    parent_uuid=item_data.get('parent_uuid'),
                )
            elif item_data == strategic.objective:
                item = Objective(
                    uuid=uuid,
                    name=item_data['name'],
                    description=item_data.get('description'),
                    slug=item_data['slug'],
                    status=item_data.get('status', 'pending'),
                    parent_uuid=item_data.get('parent_uuid'),
                )
            else:
                continue

            all_items[uuid] = item
        
        # Load execution items
        for del_data in execution.deliverables:
            deliverable = Deliverable(
                uuid=del_data['uuid'],
                name=del_data['name'],
                description=del_data.get('description'),
                slug=del_data['slug'],
                status=del_data.get('status', 'pending'),
                parent_uuid=del_data.get('parent_uuid'),
            )
            all_items[del_data['uuid']] = deliverable
            
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
            all_items[act_data['uuid']] = action
        
        # Build hierarchy using parent_uuid references
        for uuid, item in all_items.items():
            item_data = None
            for d in strategic_items:
                if d['uuid'] == uuid:
                    item_data = d
                    break
            if not item_data:
                for d in execution.deliverables:
                    if d['uuid'] == uuid:
                        item_data = d
                        break
            if not item_data:
                for d in execution.actions:
                    if d['uuid'] == uuid:
                        item_data = d
                        break

            if not item_data:
                continue

            parent_uuid = item_data.get('parent_uuid')
            if parent_uuid and parent_uuid in all_items:
                parent = all_items[parent_uuid]
                if isinstance(item, Milestone) and isinstance(parent, Phase):
                    parent.milestones.append(item)
                elif isinstance(item, Objective) and isinstance(parent, Milestone):
                    parent.objectives.append(item)
                elif isinstance(item, Deliverable) and isinstance(parent, Objective):
                    parent.deliverables.append(item)
                elif isinstance(item, Action) and isinstance(parent, Deliverable):
                    parent.actions.append(item)
            elif isinstance(item, Phase):
                self.project.phases.append(item)

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
