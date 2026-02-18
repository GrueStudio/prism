#!/usr/bin/env python3
"""
Migration script for converting project.json to .prism/ directory structure.

This script:
1. Reads the existing project.json file
2. Generates UUIDs for all items
3. Transforms nested structure to flat structure with parent_uuid references
4. Separates active vs completed items:
   - Active (pending/in-progress) strategic items → strategic.json
   - Active execution items → execution.json
   - Completed strategic items → archive/strategic.json
   - Completed execution trees → archive/objective-{slug}.exec.json
5. Preserves item order
6. Backs up the original project.json before migration
"""
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def is_completed(status: str) -> bool:
    """Check if an item status indicates completion."""
    return status in ('completed', 'archived')


def migrate_action(action: Dict[str, Any], parent_uuid: str) -> Dict[str, Any]:
    """Migrate an action item."""
    return {
        'uuid': generate_uuid(),
        'name': action.get('name', ''),
        'description': action.get('description'),
        'slug': action.get('slug', ''),
        'status': action.get('status', 'pending'),
        'parent_uuid': parent_uuid,
        'created_at': action.get('created_at', datetime.now().isoformat()),
        'updated_at': action.get('updated_at', datetime.now().isoformat()),
        'time_spent': action.get('time_spent'),
        'due_date': action.get('due_date'),
    }


def migrate_deliverable(
    deliverable: Dict[str, Any],
    parent_uuid: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Migrate a deliverable and its actions.
    
    Returns:
        Tuple of (migrated_deliverable, list_of_actions)
    """
    actions = []
    for action in deliverable.get('actions', []):
        actions.append(migrate_action(action, parent_uuid=None))  # Will set parent_uuid after
    
    # Fix parent_uuid for actions
    deliverable_uuid = generate_uuid()
    for action in actions:
        action['parent_uuid'] = deliverable_uuid
    
    return {
        'uuid': deliverable_uuid,
        'name': deliverable.get('name', ''),
        'description': deliverable.get('description'),
        'slug': deliverable.get('slug', ''),
        'status': deliverable.get('status', 'pending'),
        'parent_uuid': parent_uuid,
        'created_at': deliverable.get('created_at', datetime.now().isoformat()),
        'updated_at': deliverable.get('updated_at', datetime.now().isoformat()),
    }, actions


def migrate_objective(
    objective: Dict[str, Any],
    parent_uuid: str
) -> Tuple[
    Optional[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Optional[Dict[str, Any]]
]:
    """
    Migrate an objective and its deliverables/actions.
    
    Returns:
        Tuple of:
        - strategic_item (if not completed, else None)
        - execution_deliverables (if not completed, else [])
        - execution_actions (if not completed, else [])
        - archive_entry (if completed, else None) - includes objective + deliverables + actions
    """
    is_obj_completed = is_completed(objective.get('status', 'pending'))
    
    deliverables = []
    actions = []
    
    for deliverable in objective.get('deliverables', []):
        del_obj, del_actions = migrate_deliverable(deliverable, parent_uuid=None)  # Will fix parent_uuid
        del_obj['parent_uuid'] = generate_uuid() if is_obj_completed else None  # Placeholder
        deliverables.append(del_obj)
        actions.extend(del_actions)
    
    # Generate objective UUID
    objective_uuid = generate_uuid()
    
    # Fix parent_uuid for deliverables and actions
    for del_obj in deliverables:
        del_obj['parent_uuid'] = objective_uuid
    for action in actions:
        if action['parent_uuid'] is None:  # Actions that belong to deliverables
            # Find which deliverable they belong to
            for del_obj in deliverables:
                # Actions already have correct parent_uuid from migrate_deliverable
                pass
    
    migrated_objective = {
        'uuid': objective_uuid,
        'name': objective.get('name', ''),
        'description': objective.get('description'),
        'slug': objective.get('slug', ''),
        'status': objective.get('status', 'pending'),
        'parent_uuid': parent_uuid,
        'created_at': objective.get('created_at', datetime.now().isoformat()),
        'updated_at': objective.get('updated_at', datetime.now().isoformat()),
    }
    
    if is_obj_completed:
        # Archive the entire objective tree
        archive_entry = {
            'objective': migrated_objective,
            'deliverables': deliverables,
            'actions': actions,
        }
        return None, [], [], archive_entry
    else:
        return migrated_objective, deliverables, actions, None


def migrate_milestone(
    milestone: Dict[str, Any],
    parent_uuid: str
) -> Tuple[
    Dict[str, Any],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]]
]:
    """
    Migrate a milestone and its objectives.
    
    Returns:
        Tuple of:
        - migrated_milestone
        - strategic_items (non-completed objectives)
        - execution_deliverables (from active objectives)
        - execution_actions (from active objectives)
        - archive_entries (completed objectives with their trees)
    """
    strategic_items = []
    execution_deliverables = []
    execution_actions = []
    archive_entries = []
    
    milestone_uuid = generate_uuid()
    
    for objective in milestone.get('objectives', []):
        strat_item, delivs, acts, archive = migrate_objective(objective, milestone_uuid)
        
        if strat_item:
            strategic_items.append(strat_item)
            execution_deliverables.extend(delivs)
            execution_actions.extend(acts)
        if archive:
            archive_entries.append(archive)
    
    migrated_milestone = {
        'uuid': milestone_uuid,
        'name': milestone.get('name', ''),
        'description': milestone.get('description'),
        'slug': milestone.get('slug', ''),
        'status': milestone.get('status', 'pending'),
        'parent_uuid': parent_uuid,
        'created_at': milestone.get('created_at', datetime.now().isoformat()),
        'updated_at': milestone.get('updated_at', datetime.now().isoformat()),
    }
    
    return migrated_milestone, strategic_items, execution_deliverables, execution_actions, archive_entries


def migrate_phase(phase: Dict[str, Any]) -> Tuple[
    Dict[str, Any],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]]
]:
    """
    Migrate a phase and all its children.
    
    Returns:
        Tuple of:
        - migrated_phase
        - strategic_items (non-completed milestones/objectives)
        - execution_deliverables (from active objectives)
        - execution_actions (from active objectives)
        - archive_entries (completed objectives with their trees)
    """
    strategic_items = []
    execution_deliverables = []
    execution_actions = []
    archive_entries = []
    
    phase_uuid = generate_uuid()
    
    for milestone in phase.get('milestones', []):
        mile_item, strat_items, delivs, acts, archives = migrate_milestone(
            milestone, phase_uuid
        )
        
        strategic_items.append(mile_item)
        strategic_items.extend(strat_items)
        execution_deliverables.extend(delivs)
        execution_actions.extend(acts)
        archive_entries.extend(archives)
    
    migrated_phase = {
        'uuid': phase_uuid,
        'name': phase.get('name', ''),
        'description': phase.get('description'),
        'slug': phase.get('slug', ''),
        'status': phase.get('status', 'pending'),
        'parent_uuid': None,
        'created_at': phase.get('created_at', datetime.now().isoformat()),
        'updated_at': phase.get('updated_at', datetime.now().isoformat()),
    }
    
    return migrated_phase, strategic_items, execution_deliverables, execution_actions, archive_entries


def migrate_project(project_file: Path, prism_dir: Path) -> None:
    """
    Migrate project.json to .prism/ directory structure.
    
    Args:
        project_file: Path to project.json
        prism_dir: Path to .prism/ directory
    """
    # Load existing project data
    with open(project_file, 'r') as f:
        project = json.load(f)
    
    # Create .prism/ directory
    prism_dir.mkdir(exist_ok=True)
    (prism_dir / 'archive').mkdir(exist_ok=True)
    
    # Get the current active path (last phase, last milestone, last objective)
    phases = project.get('phases', [])
    if not phases:
        print("Error: No phases found in project.json")
        return

    current_phase = phases[-1]
    current_milestone = current_phase.get('milestones', [])[-1] if current_phase.get('milestones') else None
    current_objective = current_milestone.get('objectives', [])[-1] if current_milestone and current_milestone.get('objectives') else None

    # Collect all migrated data
    active_strategic_items = []  # Only current phase, milestone, objective
    active_execution_deliverables = []
    active_execution_actions = []
    archive_strategic_items = []
    archive_execution_trees = []  # List of (objective_uuid, deliverables, actions)

    # Track indices for path resolution (1-based)
    total_phases = len(phases)
    total_milestones_in_current_phase = len(current_phase.get('milestones', []))
    total_objectives_in_current_milestone = len(current_milestone.get('objectives', [])) if current_milestone else 0

    # Migrate all phases, milestones, objectives - but only keep current path active
    for phase_idx, phase in enumerate(phases):
        is_current_phase = (phase_idx == len(phases) - 1)
        phase_uuid = generate_uuid()
        
        migrated_phase = {
            'uuid': phase_uuid,
            'name': phase.get('name', ''),
            'description': phase.get('description'),
            'slug': phase.get('slug', ''),
            'status': phase.get('status', 'pending'),
            'parent_uuid': None,
            'created_at': phase.get('created_at', datetime.now().isoformat()),
            'updated_at': phase.get('updated_at', datetime.now().isoformat()),
        }
        
        if is_current_phase:
            active_strategic_items.append(migrated_phase)
        else:
            archive_strategic_items.append(migrated_phase)
        
        # Process milestones
        milestones = phase.get('milestones', [])
        for mile_idx, milestone in enumerate(milestones):
            is_current_milestone = is_current_phase and (mile_idx == len(milestones) - 1)
            milestone_uuid = generate_uuid()
            
            migrated_milestone = {
                'uuid': milestone_uuid,
                'name': milestone.get('name', ''),
                'description': milestone.get('description'),
                'slug': milestone.get('slug', ''),
                'status': milestone.get('status', 'pending'),
                'parent_uuid': phase_uuid,
                'created_at': milestone.get('created_at', datetime.now().isoformat()),
                'updated_at': milestone.get('updated_at', datetime.now().isoformat()),
            }
            
            if is_current_milestone:
                active_strategic_items.append(migrated_milestone)
            else:
                archive_strategic_items.append(migrated_milestone)
            
            # Process objectives
            objectives = milestone.get('objectives', [])
            for obj_idx, objective in enumerate(objectives):
                is_current_objective = is_current_milestone and (obj_idx == len(objectives) - 1)
                objective_uuid = generate_uuid()
                
                migrated_objective = {
                    'uuid': objective_uuid,
                    'name': objective.get('name', ''),
                    'description': objective.get('description'),
                    'slug': objective.get('slug', ''),
                    'status': objective.get('status', 'pending'),
                    'parent_uuid': milestone_uuid,
                    'created_at': objective.get('created_at', datetime.now().isoformat()),
                    'updated_at': objective.get('updated_at', datetime.now().isoformat()),
                }
                
                # Process deliverables and actions
                deliverables = []
                actions = []
                for deliverable in objective.get('deliverables', []):
                    del_uuid = generate_uuid()
                    
                    migrated_deliverable = {
                        'uuid': del_uuid,
                        'name': deliverable.get('name', ''),
                        'description': deliverable.get('description'),
                        'slug': deliverable.get('slug', ''),
                        'status': deliverable.get('status', 'pending'),
                        'parent_uuid': objective_uuid,
                        'created_at': deliverable.get('created_at', datetime.now().isoformat()),
                        'updated_at': deliverable.get('updated_at', datetime.now().isoformat()),
                    }
                    
                    # Process actions
                    for action in deliverable.get('actions', []):
                        action_uuid = generate_uuid()
                        
                        migrated_action = {
                            'uuid': action_uuid,
                            'name': action.get('name', ''),
                            'description': action.get('description'),
                            'slug': action.get('slug', ''),
                            'status': action.get('status', 'pending'),
                            'parent_uuid': del_uuid,
                            'created_at': action.get('created_at', datetime.now().isoformat()),
                            'updated_at': action.get('updated_at', datetime.now().isoformat()),
                            'time_spent': action.get('time_spent'),
                            'due_date': action.get('due_date'),
                        }
                        actions.append(migrated_action)
                    
                    deliverables.append(migrated_deliverable)
                
                if is_current_objective:
                    active_strategic_items.append(migrated_objective)
                    active_execution_deliverables.extend(deliverables)
                    active_execution_actions.extend(actions)
                else:
                    archive_strategic_items.append(migrated_objective)
                    archive_execution_trees.append((migrated_objective['uuid'], deliverables, actions))
    
    # Save strategic.json (active items only: current phase, milestone, objective)
    strategic_file = prism_dir / 'strategic.json'
    with open(strategic_file, 'w') as f:
        json.dump({
            'phase': active_strategic_items[0] if len(active_strategic_items) > 0 else None,
            'milestone': active_strategic_items[1] if len(active_strategic_items) > 1 else None,
            'objective': active_strategic_items[2] if len(active_strategic_items) > 2 else None,
            'phase_index': total_phases,  # 1-based index of current phase
            'milestone_index': total_milestones_in_current_phase,  # 1-based index within phase
            'objective_index': total_objectives_in_current_milestone,  # 1-based index within milestone
        }, f, indent=2)
    
    # Save execution.json (active items only)
    execution_file = prism_dir / 'execution.json'
    with open(execution_file, 'w') as f:
        json.dump({
            'deliverables': active_execution_deliverables,
            'actions': active_execution_actions
        }, f, indent=2)
    
    # Save archived strategic items (grouped by type)
    if archive_strategic_items:
        archive_strategic_file = prism_dir / 'archive' / 'strategic.json'
        # Get the current phase UUID to identify milestones
        current_phase_uuid = active_strategic_items[0]['uuid'] if len(active_strategic_items) > 0 else None
        current_milestone_uuid = active_strategic_items[1]['uuid'] if len(active_strategic_items) > 1 else None
        
        # Separate archived items by type
        # Phases: items with no parent_uuid
        archived_phases = [item for item in archive_strategic_items if item.get('parent_uuid') is None]
        # Milestones: items whose parent_uuid is a phase (either archived or current)
        all_phase_uuids = [p['uuid'] for p in archived_phases]
        if current_phase_uuid:
            all_phase_uuids.append(current_phase_uuid)
        archived_milestones = [item for item in archive_strategic_items if item.get('parent_uuid') in all_phase_uuids]
        # Objectives: everything else (parent is a milestone)
        all_milestone_uuids = [m['uuid'] for m in archived_milestones]
        if current_milestone_uuid:
            all_milestone_uuids.append(current_milestone_uuid)
        archived_objectives = [item for item in archive_strategic_items if item.get('parent_uuid') in all_milestone_uuids]
        
        with open(archive_strategic_file, 'w') as f:
            json.dump({
                'phases': archived_phases,
                'milestones': archived_milestones,
                'objectives': archived_objectives,
            }, f, indent=2)
    
    # Save archived execution trees (one file per non-current objective)
    for obj_uuid, deliverables, actions in archive_execution_trees:
        archive_exec_file = prism_dir / 'archive' / f'{obj_uuid}.exec.json'
        with open(archive_exec_file, 'w') as f:
            json.dump({
                'deliverables': deliverables,
                'actions': actions
            }, f, indent=2)
    
    # Save config.json
    config_file = prism_dir / 'config.json'
    config = {
        'schema_version': '0.2.0',
        'slug_max_length': 64,
        'slug_regex_pattern': '^[a-z0-9-]+$',
        'slug_word_limit': 5,
        'slug_filler_words': [
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'were', 'will', 'with'
        ],
        'date_formats': ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'],
        'date_max_years_future': 10,
        'date_max_years_past': 50,
        'status_header_width': 25,
        'percentage_round_precision': 1,
    }
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Save orphans.json (empty initially)
    orphans_file = prism_dir / 'orphans.json'
    with open(orphans_file, 'w') as f:
        json.dump({'orphans': []}, f, indent=2)


def main():
    """Main entry point for the migration script."""
    project_file = Path('project.json')
    prism_dir = Path('.prism')
    backup_file = Path('project.json.backup')
    
    if not project_file.exists():
        print(f"Error: {project_file} not found")
        return 1
    
    # Create backup
    print(f"Creating backup: {backup_file}")
    shutil.copy2(project_file, backup_file)
    
    # Run migration
    print(f"Migrating {project_file} to {prism_dir}/")
    migrate_project(project_file, prism_dir)
    
    print("Migration complete!")
    print(f"  - Active strategic items: .prism/strategic.json")
    print(f"  - Active execution items: .prism/execution.json")
    print(f"  - Configuration: .prism/config.json")
    print(f"  - Orphans: .prism/orphans.json")
    print(f"  - Archived strategic items: .prism/archive/strategic.json")
    print(f"  - Archived execution trees: .prism/archive/*.exec.json")
    print(f"  - Backup: {backup_file}")
    
    return 0


if __name__ == '__main__':
    exit(main())
