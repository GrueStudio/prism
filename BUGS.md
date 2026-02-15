# Bugs

This file tracks bugs and issues for the Prism CLI.

---
## Known Bugs:

* Parents completion not cascading (Issue #1): When all child items of a parent are marked as complete, the parent is not automatically marked as complete. This affects the task progression system where completing all actions in a deliverable should mark the deliverable as complete and move to the next deliverable.

* Task progression crosses deliverable boundaries (Issue #2): The task system progresses linearly through all pending actions across different deliverables rather than completing one deliverable before moving to the next. This causes confusion when working on related deliverables that build upon each other, as completing tasks for one deliverable can advance the cursor to tasks in other deliverables.

* Task completion behavior incorrect (Issue #3): The `prism task done` command currently completes the current task AND starts the next task. The correct behavior should be: `prism task done` only completes the current task, while `prism task next` should complete the current task AND start the next task. This creates confusion about which task is currently active.

## Fixed Bugs:

* None currently.