# Future Ideas (Orphan Ideas)

This file tracks future ideas and enhancements for the Prism CLI that are not currently part of any active phase, milestone, or objective. These are "orphan" ideas that will be prioritized and structured into strategic items at a later time.

---
## Ideas:

*   **Implement `prism bug` command:**
    *   Define `Bug` Pydantic model.
    *   Implement `prism bug add <title> --desc <description> --priority (low|medium|high)`.
    *   Implement `prism bug list [--status <status>]`.
    *   Implement `prism bug show <id/slug>`.
    *   Implement `prism bug status <id/slug> (open|in-progress|closed)`.
*   **Implement `prism idea` command:**
    *   Define `Idea` Pydantic model.
    *   Implement `prism idea add <title> --desc <description> --tags <tag1,tag2>`.
    *   Implement `prism idea list [--tag <tag>]`.
    *   Implement `prism idea show <id/slug>`.
*   **Implement time tracking:**
    *   Implement `prism time start <action_path>`.
    *   Implement `prism time stop <action_from_path>`.
    *   Implement `prism time report`.
    *   Implement logic for "cursor" or "current" action tracking.
*   **Enhance `prism status` command:**
    *   Add filtering options (e.g., `--phase`, `--milestone`) to the `prism status` command.
    *   Provide more detailed summaries.
*   **Implement `prism strat list` and `prism exec list` with filtering options.**
*   **Enhance user feedback and error messages for path resolution.**

---
## Improvements & Architectural Concerns from build/0.1.1 Review:

1.  **Persistence Layer Abstraction:**
    *   **Concern:** The `Tracker` class currently tightly couples persistence logic (loading/saving `project.json`).
    *   **Future:** Abstract this to a dedicated layer (`prism/data_store.py`) to allow for different storage backends (e.g., SQLite, a simple database, or even remote storage) and improve modularity/testability.

2.  **Performance with Large Projects:**
    *   **Concern:** Loading and saving the *entire* `project.json` on every command execution could become a performance bottleneck for very large project files.
    *   **Future:** Consider implementing partial loading/saving or a more efficient data structure/database.

3.  **`get_current_objective` Refinement:**
    *   **Concern:** The current `get_current_objective` logic (most recently created, uncompleted) might not always align with complex project management strategies.
    *   **Future:** Introduce configuration options or CLI commands to allow users to explicitly set or re-prioritize the "current" objective, or to navigate between objectives more directly.

4.  **Flexible Action Status Management:**
    *   **Concern:** No explicit `skip_action`, `pause_action`, or `revert_action_status` commands.
    *   **Future:** Add commands for more user control over task flow, allowing temporary bypasses or mistake correction.

5.  **Enhanced Error Handling:**
    *   **Concern:** The `Tracker` currently re-raises raw exceptions (e.g., `ValidationError`).
    *   **Future:** Implement more user-friendly error messages and potentially custom exception types for different failure scenarios.

6.  **Progress Tracking and Reporting:**
    *   **Concern:** `prism status` could be enhanced to show progress specifically related to the active cursor.
    *   **Future:** Extend `prism status` or introduce new reporting commands to visualize task progress, time spent, and upcoming tasks.

7.  **Input Validation for Path-Based Commands:**
    *   **Concern:** While `get_item_by_path` handles invalid paths by returning `None`, the CLI commands that use it might benefit from more explicit validation and user feedback.
    *   **Future:** Provide immediate feedback when a user inputs a non-existent path.

---
## Beta Enhancements (Post-Alpha):

1.  **`--no-cascade` flag for `prism task done`:**
    *   **Idea:** Add optional `--no-cascade` flag to prevent automatic parent completion.
    *   **Use case:** Advanced users who want fine-grained control over status propagation.
    *   **Implementation:** Pass flag through to `complete_current_action(no_cascade=True)`.

2.  **Complete empty deliverables/objectives (non-action items):**
    *   **Idea:** Allow manual completion of deliverables or objectives that have no children.
    *   **Use case:** Some deliverables may be documentation or research tasks with no sub-actions.
    *   **Implementation:** Add `prism exec complete <path>` command for manual completion of any execution item.
    *   **Note:** Currently empty deliverables don't auto-complete to prevent accidental completion.

3.  **Undo/reopen mechanism:**
    *   **Idea:** Add ability to reopen completed items or undo cascade completion.
    *   **Use case:** Accidental completion requires manual editing of project.json currently.
    *   **Implementation:** Add `prism reopen <path>` command that resets status to previous state.

4.  **Action priority/reordering:**
    *   **Idea:** Add `priority` field to actions and sort by priority within deliverable.
    *   **Use case:** Some actions are more important than others within same deliverable.
    *   **Implementation:** Add `--priority (high|medium|low)` to `prism exec add --action`, sort actions by priority in `_find_next_pending_action_in_deliverable()`.

5.  **Batch task completion:**
    *   **Idea:** Add `--count N` flag to `prism task done` to complete multiple actions at once.
    *   **Use case:** Quickly complete several small tasks without repeated commands.
    *   **Implementation:** Loop `complete_current_action()` N times with single save.

---
## 1.0 Enhancements (Pre-Stable):

1.  **Split Core.py into focused classes:**
    *   **Concern:** Core class is 690+ lines with 20+ methods handling multiple responsibilities.
    *   **Future:** Extract `TaskManager` (task operations), `CompletionTracker` (cascade logic), `ItemCRUD` (add/update/delete).
    *   **Benefit:** Easier to test, understand, and maintain.

2.  **Schema versioning and migration:**
    *   **Concern:** No version field in `project.json`. Schema changes would break existing files.
    *   **Future:** Add `schema_version` field to ProjectData, implement migration logic in DataStore.
    *   **Benefit:** Safe evolution of data model across versions.

3.  **Lazy loading for large projects:**
    *   **Concern:** Entire JSON loaded on every command. 1000+ actions could be slow.
    *   **Future:** Cache frequently accessed data, load subtrees on demand.
    *   **Benefit:** Better performance with large project files.

4.  **Status command refactoring:**
    *   **Concern:** `status.py` is 219 lines handling text output, JSON, current deliverable, overdue, orphaned.
    *   **Future:** Extract `StatusFormatter` (output formatting), `OverdueChecker` (date comparisons).
    *   **Benefit:** Cleaner separation of concerns, easier to extend.

5.  **Cursor management improvement:**
    *   **Concern:** After `task done`, cursor points to completed action until `task start` is called.
    *   **Future:** Clear cursor on completion, or update to next pending action automatically.
    *   **Benefit:** Clearer indication of current task state.

6.  **File locking for concurrent access:**
    *   **Concern:** No file locking on `project.json`. Two terminals could corrupt data.
    *   **Future:** Use `fcntl` (Unix) or `msvcrt` (Windows) for exclusive file locks in DataStore.
    *   **Benefit:** Safe concurrent access from multiple terminals.

7.  **Timezone-aware datetimes:**
    *   **Concern:** `datetime.now()` uses local time without timezone info.
    *   **Future:** Use `datetime.now(timezone.utc)` throughout, store timezone in config.
    *   **Benefit:** Correct date comparisons across timezones and DST changes.

---
## Architectural Concerns (Post-Refactor):

1.  **Signal Descriptor uses instance as dictionary key:**
    *   **Concern:** `SignalDescriptor.instance_signals` uses the instance object as a dictionary key. This is fragile because if `__hash__()` changes behavior (e.g., based on load state), signal connections are lost.
    *   **Current workaround:** `ArchivedItem.__hash__()` always returns `hash(id(self))` to ensure stability.
    *   **Future:** Refactor signal system to not rely on instance identity as dictionary keys. Consider using `id(obj)` directly or a weak reference-based approach.
    *   **Benefit:** More robust signal system that doesn't depend on hash stability hacks.

2.  **item_type validation in get_archived_item():**
    *   **Concern:** `ArchiveManager.get_archived_item(uuid, item_type)` accepts `item_type` from caller but doesn't validate it against what actually exists in the archive.
    *   **Current behavior:** Creates wrapper with given `item_type`, only fails when accessing properties if item doesn't exist.
    *   **Future:** Add validation to check if UUID exists in archive and verify item_type matches before creating wrapper.
    *   **Benefit:** Earlier error detection, clearer error messages for invalid UUIDs.