# Development Plan for Prism CLI

This document outlines the strategic and execution items for the development of the Prism CLI, using the very methodology that the CLI is designed to implement.

---

## Strategic Items

### Phase: Pre-Alpha - Working towards absolute core functionality

**Guiding Philosophy:** Establish the foundational CLI structure, data modeling, and local data persistence via JSON. Focus on basic creation and viewing of strategic and execution items.

#### Milestone: Initial CLI Setup & Data Persistence

**Features:** Basic project structure, Pydantic data models for all item types, robust JSON data storage, core tracker logic for item management, and initial CLI commands for adding and showing items.

##### Objective: Basic CLI commands & JSON storage (Completed)

**Features:** The ability to add phases, milestones, objectives, deliverables, and actions, and to view their details, all persisted in a JSON file.

###### Deliverable: Setup Project Structure (Completed)
*   **Action:** Create core project folders (`src/`, `tests/`, `docs/`, `scripts/`, `prism/`).
*   **Action:** Create `pyproject.toml` with basic project metadata and `click`, `Pydantic` dependencies.
*   **Action:** Create `README.md` and `.gitignore`.
*   **Action:** Create `__init__.py` files in `prism/` and `prism/commands/`.

###### Deliverable: Define Data Models (Completed)
*   **Action:** Implement `BaseItem` Pydantic model with `id`, `name`, `description`, `slug`, `status`, `created_at`, `updated_at`.
*   **Action:** Implement slug generation/validation logic in `BaseItem` (kebab-case, max 10 chars, uniqueness within parent scope).
*   **Action:** Implement `Phase` model (current, list of Milestones).
*   **Action:** Implement `Milestone` model (list of Objectives).
*   **Action:** Implement `Objective` model (list of Deliverables).
*   **Action:** Implement `Deliverable` model (list of Actions).
*   **Action:** Implement `Action` model (time_spent, due_date).
*   **Action:** Implement `ProjectData` as the root model containing all phases.

###### Deliverable: Implement JSON Data Store (Completed)
*   **Action:** Create `DataStore` class in `prism/data_store.py`.
*   **Action:** Implement `load_project_data(file_path: Path) -> ProjectData` method.
*   **Action:** Implement `save_project_data(data: ProjectData, file_path: Path)` method.
*   **Action:** Handle default project file location (e.g., `~/.config/prism/project.json` or current directory).
*   **Action:** Implement logic to initialize an empty `ProjectData` if no file exists.

###### Deliverable: Implement Core Tracker Logic (Completed)
*   **Action:** Create `Tracker` class in `prism/tracker.py` to encapsulate `ProjectData` management.
*   **Action:** Implement `add_item(parent_path: str, item_type: str, name: str, description: Optional[str])` method.
*   **Action:** Implement `get_item_by_path(path: str) -> Optional[BaseItem]` method (resolves slug/number paths).
*   **Action:** Implement `_resolve_path_segment(items: List[BaseItem], segment: str) -> Optional[BaseItem]` utility.
*   **Action:** Implement `_generate_unique_slug(parent_items: List[BaseItem], base_name: str) -> str` utility.

###### Deliverable: Basic CLI Commands (Completed)
*   **Action:** Modify `prism/cli.py` to import and register `strat` and `exec` command groups.
*   **Action:** Implement `prism strat add --phase/--milestone/--objective --name <name> --desc <description> [--parent-path <path>]`.
*   **Action:** Implement `prism exec add --deliverable/--action --name <name> --desc <description> [--parent-path <path>]`.
*   **Action:** Implement `prism strat show --path <path_to_item>` to display details and children.
*   **Action:** Implement `prism exec show --path <path_to_item>` to display details and children.
*   **Action:** Implement validation in `prism strat add` to prevent strategic item additions if the associated objective lacks a complete execution tree.
*   **Action:** Implement `prism exec addtree <json_file_path> [--mode <append|replace>]` to add an entire execution tree from a JSON file.

#### Milestone: Core CRUD Operations

**Features:** Full Create, Read, Update, Delete (CRUD) functionality for all strategic and execution items, plus enhanced output and enforced business rules.

##### Objective: Implement Update and Delete Commands (Completed)

**Features:** Implement `edit` and `delete` commands for all strategic and execution item types.

###### Deliverable: Implement Update Commands (Completed)

*   **Action:** Implement `prism strat edit --path <path_to_item> [--name <name>] [--desc <description>]`
*   **Action:** Implement `prism strat edit --path <path_to_item> --file <json_file_path>`
*   **Action:** Implement `prism exec edit --path <path_to_item> [--name <name>] [--desc <description>] [--due-date <date>]`
*   **Action:** Implement `prism exec edit --path <path_to_item> --file <json_file_path>`

###### Deliverable: Implement Delete Commands (Completed)

*   **Action:** Implement `prism strat delete --path <path_to_item>`
*   **Action:** Implement `prism exec delete --path <path_to_item>`

###### Deliverable: Streamline addtree Input (Completed)

*   **Action:** Simplify the input JSON structure for `prism exec addtree` (e.g., remove redundant object wrapping for objectives/deliverables).

##### Objective: Enhance CLI Output and Enforce Business Rules (Completed)

**Features:** Provide machine-readable output for CLI commands and enforce rules regarding item status changes.

###### Deliverable: Implement Structured Output for Show Commands (Completed)

*   **Action:** Add `--json` flag to `prism strat show` and `prism exec show` to output item details in machine-readable JSON format.

###### Deliverable: Implement Status Command (Completed)

*   **Action:** Implement `prism status` command to display a summary of project progress, including counts of pending/completed items, overdue actions, and orphaned items.
*   **Action:** Consider adding filtering options (e.g., `--phase`, `--milestone`) to the `prism status` command.

###### Deliverable: Enforce Item Status Rules (Completed)

*   **Action:** Modify `prism strat edit` and `prism exec edit` to prevent updates to items with a "completed" or "archived" status.
*   **Action:** Modify `prism strat add` and `prism exec add` to ensure new items cannot be created with a "completed" or "archived" status, implicitly setting them to "pending".
*   **Action:** Modify `prism strat delete` and `prism exec delete` to prevent deletion of items with a "completed" or "archived" status.

---

## Execution Items (Future)

These items represent the next steps beyond the current Pre-Alpha phase.

### Phase: Alpha - Basic CRUD for all item types, time tracking, bug tracking placeholder

#### Milestone: CRUD & Basic Time Tracking

##### Objective: Full CRUD & Time Tracking Start

###### Deliverable: Full CRUD Operations

*   **Action:** Implement `edit` commands for all item types in `strat` and `exec` using `--path`.
*   **Action:** Implement `delete` commands for all item types in `strat` and `exec` using `--path`.
*   **Action:** Implement `status` update commands for all trackable items.

###### Deliverable: Initial Time Tracking

*   **Action:** Implement `prism time start <action_path>`.
*   **Action:** Implement `prism time stop <action_from_path>`.
*   **Action:** Implement `prism time report`.
*   **Action:** Implement logic for "cursor" or "current" action tracking.

### Phase: Beta - Enhanced features, multi-user preparation

#### Milestone: Ideas, Bug Tracking & Refinements

##### Objective: Ideas & Bug Tracking

###### Deliverable: Ideas Management

*   **Action:** Define `Idea` Pydantic model.
*   **Action:** Implement `prism idea add <title> --desc <description> --tags <tag1,tag2>`.
*   **Action:** Implement `prism idea list [--tag <tag>]`.
*   **Action:** Implement `prism idea show <id/slug>`.

###### Deliverable: Bug Tracking (JSON based)

*   **Action:** Define `Bug` Pydantic model.
*   **Action:** Implement `prism bug add <title> --desc <description> --priority (low|medium|high)`.
*   **Action:** Implement `prism bug list [--status <status>]`.
*   **Action:** Implement `prism bug show <id/slug>`.
*   **Action:** Implement `prism bug status <id/slug> (open|in-progress|closed)`.

##### Objective: Improved CLI & Path Resolution

###### Deliverable: Command Refinements

*   **Action:** Implement `prism strat list` and `prism exec list` with filtering options.
*   **Action:** Enhance user feedback and error messages for path resolution.