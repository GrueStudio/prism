"""
Project model for the Prism CLI.

In-memory project data with hierarchical structure.
Built from flat storage on load.
Flattened back to storage on save.

Archived items are represented as ArchivedItem wrappers for lazy loading.
"""

from typing import Dict, List

from prism.models.archived import ArchivedItem
from prism.models.base import BaseItem, Phase


class Project:
    """
    In-memory project data with hierarchical structure.

    Built from flat storage on load.
    Flattened back to storage on save.

    Archived items are represented as ArchivedItem wrappers for lazy loading.
    """

    def __init__(self, child_uuids: List[str]):
        self.child_uuids = child_uuids
        self.phases: List[BaseItem | ArchivedItem | None] = []
        self._id_map: Dict[str, BaseItem] = {}
        self.task_cursor: str | None = None
        self.crud_context: str | None = None

    def add_child(self, item: Phase | ArchivedItem):
        if item.uuid not in self.child_uuids:
            self.child_uuids.append(item.uuid)
            self.phases.append(item)
        else:
            index = self.child_uuids.index(item.uuid)
            self.phases[index] = item
        self._map_item(item)

    def _map_item(self, item: BaseItem | ArchivedItem):
        if isinstance(item, BaseItem) and item.uuid not in self._id_map:
            self._id_map[item.uuid] = item

    def place_item(self, item: BaseItem | ArchivedItem):
        if item.parent_uuid and item.parent_uuid in self._id_map:
            parent = self._id_map[item.parent_uuid]
            if isinstance(parent, BaseItem):
                parent.add_child(item)
            elif isinstance(parent, ArchivedItem):
                parent.add_child(item)
        self._map_item(item)

    def get_item(self, uuid: str) -> BaseItem | None:
        return self._id_map.get(uuid)

    def build_maps(self) -> None:
        """Rebuild the UUID to item lookup map.

        Traverses the entire tree and maps all BaseItem UUIDs.
        Called after bulk operations that add items.
        """
        self._id_map.clear()

        def _traverse(items: List):
            for item in items:
                if isinstance(item, BaseItem):
                    self._id_map[item.uuid] = item
                    if item.children:
                        _traverse(item.children)

        _traverse(self.phases)
