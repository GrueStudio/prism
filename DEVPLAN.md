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

**Features:** Full Create, Read, Update, Delete (CRUD) functionality for all strategic and execution items, plus enhanced output.

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

##### Objective: Enhance CLI Output and Enforce Business Rules

**Features:** Provide machine-readable output for CLI commands and enforce rules regarding item status changes.

###### Deliverable: Implement Structured Output for Show Commands

*   **Action:** Add `--json` flag to `prism strat show` and `prism exec show` to output item details in machine-readable JSON format.

###### Deliverable: Enforce Item Status Rules

*   **Action:** Modify `prism strat edit` and `prism exec edit` to prevent updates to items with a "completed" or "archived" status.
*   **Action:** Modify `prism strat add` and `prism exec add` to ensure new items cannot be created with a "completed" or "archived" status, implicitly setting them to "pending".
