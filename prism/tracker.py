from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from pydantic import ValidationError

from prism.models import ProjectData, Phase, Milestone, Objective, Deliverable, Action, BaseItem

class Tracker:
    def __init__(self, project_file: Optional[Path] = None):
        self.project_file = project_file if project_file else Path("project.json") # Default for testing
        self.project_data = self._load_project_data()

    def _load_project_data(self) -> ProjectData:
        if self.project_file.exists():
            try:
                with open(self.project_file, 'r') as f:
                    data = json.load(f)
                return ProjectData.parse_obj(data)
            except (json.JSONDecodeError, ValidationError) as e:
                # For now, just re-raise. In a real app, we might handle this more gracefully.
                raise Exception(f"Error loading project data from {self.project_file}: {e}")
        return ProjectData()

    def _save_project_data(self):
        with open(self.project_file, 'w') as f:
            json.dump(self.project_data.dict(), f, indent=2)

        class Tracker:

            def __init__(self, project_file: Optional[Path] = None):

                self.project_file = project_file if project_file else Path("project.json") # Default for testing

                self.project_data = self._load_project_data()

        

            def _load_project_data(self) -> ProjectData:

                if self.project_file.exists():

                    try:

                        with open(self.project_file, 'r') as f:

                            data = json.load(f)

                        return ProjectData.parse_obj(data)

                    except (json.JSONDecodeError, ValidationError) as e:

                        # For now, just re-raise. In a real app, we might handle this more gracefully.

                        raise Exception(f"Error loading project data from {self.project_file}: {e}")

                return ProjectData()

        

            def _save_project_data(self):

                with open(self.project_file, 'w') as f:

                    json.dump(self.project_data.dict(), f, indent=2)

        

            def _generate_unique_slug(self, existing_items: List[BaseItem], base_name: str) -> str:

                base_slug = re.sub(r'[^a-z0-9]+', '-', base_name.lower()).strip('-')[:10]

                if not base_slug:

                    base_slug = "item"

        

                existing_slugs = {item.slug for item in existing_items}

                

                slug = base_slug

                count = 1

                while slug in existing_slugs:

                    slug = f"{base_slug[:(10 - len(str(count)) - 1)]}-{count}" if len(base_slug) > (10 - len(str(count)) - 1) else f"{base_slug}-{count}"

                    count += 1

                return slug

        

            def _resolve_path_segment(self, items: List[BaseItem], segment: str) -> Optional[BaseItem]:

                # Try to match by slug

                for item in items:

                    if item.slug == segment:

                        return item

                

                # Try to match by index (e.g., "milestones/1")

                try:

                    index = int(segment) - 1

                    if 0 <= index < len(items):

                        return items[index]

                except ValueError:

                    pass # Not an integer, continue

        

                return None

        

            def get_item_by_path(self, path: str) -> Optional[BaseItem]:

                segments = path.split('/')

                current_items: List[BaseItem] = list(self.project_data.phases)

                

                target_item: Optional[BaseItem] = None

        

                for i, segment in enumerate(segments):

                    found_item = self._resolve_path_segment(current_items, segment)

                    if not found_item:

                        return None

                    

                    target_item = found_item

                    

                    if i < len(segments) - 1: # If not the last segment, update current_items for next iteration

                        if isinstance(found_item, Phase):

                            current_items = list(found_item.milestones)

                        elif isinstance(found_item, Milestone):

                            current_items = list(found_item.objectives)

                        elif isinstance(found_item, Objective):

                            current_items = list(found_item.deliverables)

                        elif isinstance(found_item, Deliverable):

                            current_items = list(found_item.actions)

                        else:

                            return None # No children for this item type

                

                return target_item

        

            def add_item(self, item_type: str, name: str, description: Optional[str], parent_path: Optional[str]):

                # Validate item_type

                if item_type not in ['phase', 'milestone', 'objective', 'deliverable', 'action']:

                    raise ValueError(f"Invalid item type: {item_type}")

        

                # Determine the list of items to check for slug uniqueness

                items_to_check: List[BaseItem]

                if parent_path:

                    parent_item = self.get_item_by_path(parent_path)

                    if not parent_item:

                        raise ValueError(f"Parent item not found at path: {parent_path}")

                    

                    if item_type == 'milestone' and isinstance(parent_item, Phase):

                        items_to_check = parent_item.milestones

                    elif item_type == 'objective' and isinstance(parent_item, Milestone):

                        items_to_check = parent_item.objectives

                    elif item_type == 'deliverable' and isinstance(parent_item, Objective):

                        items_to_check = parent_item.deliverables

                    elif item_type == 'action' and isinstance(parent_item, Deliverable):

                        items_to_check = parent_item.actions

                    else:

                        raise ValueError(f"Cannot add {item_type} to parent of type {type(parent_item).__name__}")

                else:

                    if item_type == 'phase':

                        items_to_check = self.project_data.phases

                    else:

                        raise ValueError(f"Cannot add {item_type} without a parent path.")

                

                slug = self._generate_unique_slug(items_to_check, name)

        

                new_item: BaseItem

                if item_type == 'phase':

                    new_item = Phase(name=name, description=description, slug=slug)

                elif item_type == 'milestone':

                    new_item = Milestone(name=name, description=description, slug=slug)

                elif item_type == 'objective':

                    new_item = Objective(name=name, description=description, slug=slug)

                elif item_type == 'deliverable':

                    new_item = Deliverable(name=name, description=description, slug=slug)

                elif item_type == 'action':

                    new_item = Action(name=name, description=description, slug=slug)

                else:

                    raise ValueError("Unsupported item type during instantiation.")

                

                if parent_path:

                    # Re-fetch parent_item as it might have been modified by adding slug

                    parent_item = self.get_item_by_path(parent_path)

                    if not parent_item: # Should not happen if it was found before

                        raise ValueError(f"Parent item not found at path: {parent_path}")

                    

                    if item_type == 'milestone' and isinstance(parent_item, Phase):

                        parent_item.milestones.append(new_item)

                    elif item_type == 'objective' and isinstance(parent_item, Milestone):

                        parent_item.objectives.append(new_item)

                    elif item_type == 'deliverable' and isinstance(parent_item, Objective):

                        parent_item.deliverables.append(new_item)

                    elif item_type == 'action' and isinstance(parent_item, Deliverable):

                        parent_item.actions.append(new_item)

                else:

                    if item_type == 'phase':

                        self.project_data.phases.append(new_item)

                

                self._save_project_data()

        

            def update_item(self, path: str, name: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None):

                item_to_update = self.get_item_by_path(path)

                if not item_to_update:

                    raise ValueError(f"Item not found at path: {path}")

                

                updated = False

                if name is not None:

                    item_to_update.name = name

                    # Re-generate slug if name changes and it's not explicitly set

                    if not isinstance(item_to_update, Action): # Action slugs are derived from name but can't be changed by edit name

                        item_to_update.slug = self._generate_unique_slug(self._get_parent_items_for_slug_check(path), name)

                    updated = True

                if description is not None:

                    item_to_update.description = description

                    updated = True

                

                # Status update is not allowed from here as per deliverable

                # if status is not None:

                #     item_to_update.status = status

                #     updated = True

        

                if updated:

                    item_to_update.updated_at = datetime.now()

                    self._save_project_data()

                else:

                    raise ValueError("No update parameters provided.")

        

            def _get_parent_items_for_slug_check(self, path: str) -> List[BaseItem]:

                # Helper to get the list of siblings for slug uniqueness check

                segments = path.split('/')

                if len(segments) == 1: # Top-level phase

                    return self.project_data.phases

                

                parent_path = '/'.join(segments[:-1])

                parent_item = self.get_item_by_path(parent_path)

                

                if isinstance(parent_item, Phase):

                    return parent_item.milestones

                elif isinstance(parent_item, Milestone):

                    return parent_item.objectives

                elif isinstance(parent_item, Objective):

                    return parent_item.deliverables

                elif isinstance(parent_item, Deliverable):

                    return parent_item.actions

                return []

        

            def is_exec_tree_complete(self, objective_path: str) -> bool:

                """

                Checks if the execution tree (deliverables and actions) for a given objective is complete.

                For now, this is a placeholder and always returns True.

                """

                objective = self.get_item_by_path(objective_path)

                if not isinstance(objective, Objective):

                    return False # Or raise an error, depending on desired strictness

        

                # Placeholder logic: An objective's exec tree is "complete" if it has at least one deliverable

                # In the future, this would check if all deliverables have actions, and if all actions are 'completed', etc.

                return len(objective.deliverables) > 0

        

            def add_exec_tree(self, tree_data: List[Dict[str, Any]], mode: str):

                """

                Adds an execution tree (objectives, deliverables, actions) from a list of dicts.

                The tree_data is expected to be a list of objective-like dictionaries with nested

                deliverables and actions, following the simplified structure.

                """

                if mode == 'replace':

                    self.project_data.phases = [] # Clear all data (simplistic for now)

                    # Re-initialize to ensure a default structure for adding if replacing everything

                    self.project_data.phases.append(Phase(name="Default Phase", slug=self._generate_unique_slug(self.project_data.phases, "Default Phase")))

                    self.project_data.phases[0].milestones.append(Milestone(name="Default Milestone", slug=self._generate_unique_slug(self.project_data.phases[0].milestones, "Default Milestone")))

                elif mode != 'append':

                    raise ValueError(f"Invalid mode: {mode}. Must be 'append' or 'replace'.")

                

                # Ensure there's at least one phase and milestone to attach objectives to

                if not self.project_data.phases:

                    self.project_data.phases.append(Phase(name="Default Phase", slug=self._generate_unique_slug(self.project_data.phases, "Default Phase")))

                if not self.project_data.phases[0].milestones:

                    self.project_data.phases[0].milestones.append(Milestone(name="Default Milestone", slug=self._generate_unique_slug(self.project_data.phases[0].milestones, "Default Milestone")))

                

                target_milestone = self.project_data.phases[0].milestones[-1] # Add to the last milestone of the first phase

        

                for obj_data in tree_data:

                    obj_name = obj_data.get("name")

                    obj_desc = obj_data.get("description")

                    if not obj_name:

                        raise ValueError("Objective name is required in addtree input.")

                    

                    objective_slug = self._generate_unique_slug(target_milestone.objectives, obj_name)

                    new_objective = Objective(name=obj_name, description=obj_desc, slug=objective_slug)

                    

                    for del_data in obj_data.get("deliverables", []):

                        del_name = del_data.get("name")

                        del_desc = del_data.get("description")

                        if not del_name:

                            raise ValueError("Deliverable name is required in addtree input.")

                        

                        deliverable_slug = self._generate_unique_slug(new_objective.deliverables, del_name)

                        new_deliverable = Deliverable(name=del_name, description=del_desc, slug=deliverable_slug)

                        

                        for act_data in del_data.get("actions", []):

                            act_name = act_data.get("name")

                            act_desc = act_data.get("description")

                            if not act_name:

                                raise ValueError("Action name is required in addtree input.")

                            

                            action_slug = self._generate_unique_slug(new_deliverable.actions, act_name)

                            new_action = Action(name=act_name, description=act_desc, slug=action_slug)

                            new_deliverable.actions.append(new_action)

                        

                        new_objective.deliverables.append(new_deliverable)

                    

                    target_milestone.objectives.append(new_objective)

                

                self._save_project_data()

        

    