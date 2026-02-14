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
