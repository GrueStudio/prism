# Bugs

This file tracks bugs and issues for the Prism CLI.

---
## Known Bugs:

* **Cursor points to completed action:** After completing a task with `prism task done`, the cursor still points to the completed action until `prism task start` is called. This can cause confusion about which task is currently active.

* **No concurrent access protection:** The `DataStore` does not use file locking when reading/writing `project.json`. Running multiple Prism commands simultaneously could corrupt the project file.

* **No timezone awareness:** All datetime operations use `datetime.now()` without timezone information. This could cause issues with due date comparisons across timezones or daylight saving time changes.

## Fixed Bugs:

* **Parent completion not cascading (Issue #1):** ✓ Fixed - Completing all actions in a deliverable now marks the deliverable complete, and completing all deliverables in an objective marks the objective complete.

* **Task progression crosses deliverable boundaries (Issue #2):** ✓ Fixed - Task progression now completes all actions within a deliverable before moving to the next deliverable.

* **Task completion behavior incorrect (Issue #3):** ✓ Fixed - `prism task done` now only completes the current task, while `prism task next` completes the current task and starts the next one.