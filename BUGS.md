# Bugs

This file tracks bugs and issues for the Prism CLI.

---
## Known Bugs:

* **Cursor points to completed action:** After completing a task with `prism task done`, the cursor still points to the completed action until `prism task start` is called. This can cause confusion about which task is currently active.

* **No concurrent access protection:** The `DataStore` does not use file locking when reading/writing `project.json`. Running multiple Prism commands simultaneously could corrupt the project file.

* **No timezone awareness:** All datetime operations use `datetime.now()` without timezone information. This could cause issues with due date comparisons across timezones or daylight saving time changes.

* **Task progression crosses deliverable boundaries (Issue #4):** `prism task next` does not respect deliverable boundaries when finding the next task. When completing the last action in a deliverable, it immediately starts an action from the next deliverable instead of staying within the current deliverable context. This breaks the intended workflow of completing all actions within a deliverable before moving to the next one.

* **`prism crud delete` does not remove child UUIDs from parent:** When a deliverable is deleted using `prism crud delete`, its UUID is not removed from the parent's `child_uuids` list. This can lead to `NoneType` errors when loading the project, as the system tries to access a non-existent child. This has been remedied manually by removing the UUID from the `.prism` data, but the underlying bug remains.

## Fixed Bugs:

* **Parent completion not cascading (Issue #1):** ✓ Fixed - Completing all actions in a deliverable now marks the deliverable complete, and completing all deliverables in an objective marks the objective complete.

* **Task progression crosses deliverable boundaries (Issue #2):** ✓ Fixed - Task progression now completes all actions within a deliverable before moving to the next deliverable.

* **Task completion behavior incorrect (Issue #3):** ✓ Fixed - `prism task done` now only completes the current task, while `prism task next` completes the current task and starts the next one.