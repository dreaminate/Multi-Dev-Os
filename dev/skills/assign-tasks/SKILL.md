---
name: assign-tasks
description: Build task dependency graphs and assignment recommendations for Multi-Dev-Os task cards. Use when Codex needs to read dev/tasks TASK.md front matter, render Mermaid dependency graphs, split pending tasks into dependency components, and write a task assignment board.
---

# Assign Tasks

Use `scripts/assign_tasks.py` for deterministic task assignment planning.

## Workflow

1. Run the script from the repository root:

   ```bash
   python dev/skills/assign-tasks/scripts/assign_tasks.py --dev dev --write
   ```

2. Review `dev/tasks/ASSIGNMENT_BOARD.md`.

3. Use the board as an assignment recommendation only. Actual assignment still follows the project rule: leader/admin moves cards from `dev/tasks/pool/{uuid8}/` to `dev/tasks/{developer_id}/{uuid8}/`.

## Behavior

- Read every `TASK.md` under `dev/tasks/pool/`, active member folders, and member `done/` folders.
- Parse YAML front matter with PyYAML (`yaml.safe_load`), including `uuid` and `depends_on`.
- Build the pending dependency graph from pool tasks only, keyed by full 32-character UUID values.
- Render Mermaid for pending tasks and pending-to-pending dependency edges.
- Use logic A when pending connected component count is greater than the team member count; otherwise use logic B.
- Logic A assigns whole connected components, prefers members who own already-assigned upstream dependencies for root tasks, and falls back to logic B if the result exceeds the 20% fairness threshold.
- Logic B assigns only pending tasks with zero pending indegree, prefers upstream dependency owners, and leaves other pending tasks unassigned.

## Output

The generated board contains:

- Mermaid dependency graph.
- Assignment logic used.
- Fairness summary.
- Suggested assignments.
- Tasks intentionally left in pool.
