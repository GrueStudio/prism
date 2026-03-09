# Prism CLI

A command-line interface for project management and task tracking.

## Features (Planned)

- Strategic Planning: Define phases, milestones, and objectives.
- Execution Tracking: Manage deliverables and actions.
- Bug Tracking (Future): Track project bugs.
- Future Ideas (Future): Store unassigned ideas.
- Time Tracking (Future): Track time spent on tasks.
- Multi-user / Server-Client (Long-term Future): Collaborative functionality.

## Installation

```bash
pip install .
```

## Usage

The `prism` CLI allows you to manage your project's strategic planning and task execution.

- **View Current Status**: Get an overview of your project's progress and current focus.
  ```bash
  prism status
  ```
- **Add Project Items**: Create new phases, milestones, objectives, deliverables, or actions.
  ```bash
  prism crud add --type objective --name "Implement user authentication"
  prism crud add --type deliverable --name "Create login API endpoint"
  prism crud add --type action --name "Develop user model"
  ```
- **Manage Tasks**: Start, complete, or move to the next action.
  ```bash
  prism task start
  prism task done
  prism task next
  ```
- **Get Help**: For a full list of commands and options:
  ```bash
  prism --help
  ```

## Workflow

This project follows a specific development process that tightly integrates the `prism` CLI with a Git branching strategy. For a detailed guide on how to contribute, please read our agent instruction document.

[**>> View the Agent Instructions & Workflow <<**](AGENT.md)

## Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd prism
   ```
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Run tests:
   ```bash
   pytest
   ```
