# Gemini Development Workflow

This document outlines the Git branching and merging strategy to be followed for the Prism CLI project, as managed by the Gemini agent.

## Deliverable Workflow

When starting work on a new **Deliverable** from the `DEVPLAN.md`:

1.  **Create a New Branch:**
    *   Create a new branch named `feat/descriptive-slug`, `fix/descriptive-slug`, or `refactor/descriptive-slug` based on the nature of the deliverable.
    *   The base branch for this new branch should be the current objective's version branch (e.g., `build/0.0.1`).
    *   **Example:** For a deliverable "Define Data Models", create a branch `feat/define-data-models`.

2.  **Implement and Commit:**
    *   Implement the actions outlined in the deliverable.
    *   Commit changes regularly to this feature/fix/refactor branch.

3.  **Complete Deliverable & Merge (via GitHub PR):**
    *   Once the deliverable is complete and tested, create a Pull Request (PR) on GitHub from your `feat/` (or `fix/`, `refactor/`) branch to the current objective's version branch (e.g., `build/0.0.1`).
    *   **Code Review:** The PR will undergo a code review.
    *   **Address Immediate Issues:** Fix any issues found during the code review and commit them to the feature branch.
    *   **Create Orphans:** Identify any non-immediate concerns or potential improvements arising from the review and create new "orphan" issues/ideas for future tracking (these will later be managed by the `prism idea` or `prism bug` commands).
    *   **Squash Merge:** The PR should be **squash-merged**. The squashed commit message must adhere to conventional commit standards (`type(scope)!: message`) and the body should be a detailed explanation of the "why" for the deliverable.

## Objective Workflow

When starting work on a new **Objective** from the `DEVPLAN.md`:

1.  **Create a New Version Branch:**
    *   Create a new branch named `build/X.Y.Z` (e.g., `build/0.0.1`) from `main`.
    *   All subsequent deliverable branches for this objective will branch off this version branch.

2.  **Complete Objective & Merge to `main` (via GitHub PR):**
    *   Once all deliverables within an objective are completed and merged into the objective's version branch, and the objective itself is considered complete and stable.
    *   Create a Pull Request (PR) on GitHub from the `build/X.Y.Z` branch to the `main` branch.
    *   **Code Review:** The PR will undergo a code review.
    *   **Address Immediate Issues:** Fix any critical issues found during the code review and commit them to the `build/X.Y.Z` branch.
    *   **Create Orphans:** Identify any non-critical concerns or potential improvements and create new "orphan" issues/ideas for future tracking.
    *   **Regular Merge (No Squash):** The PR should be **regularly merged** (not squash-merged) into `main` to preserve the history of the individual deliverable squash-merges.

---

## Action and Milestone Workflow

*   **Action Items:** No specific Git workflow for individual actions. They are granular tasks within a deliverable.
*   **Milestone Items:** Milestones are collections of objectives. Their completion is marked by the completion and merging of all associated objectives.

## Dogfooding the Workflow

Initially, the `DEVPLAN.md` file will serve as the source for identifying deliverables and objectives. Once the `prism` CLI gains the necessary functionality, its commands (`prism strat show`, `prism exec show`, etc.) will be used to track progress and identify next steps, directly "dogfooding" the tool.

---

## Post-Action Reporting

After every action that makes changes to the codebase, a summary of the changes will be provided.
