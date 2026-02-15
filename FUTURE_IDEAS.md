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