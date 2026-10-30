---
name: codebase-explorer
description: "Use when the task gives an existing repository to modify or extend - maps entry points, build and test commands and the code relevant to the task before any edit. Do NOT use for tasks that start from an empty workspace or a single file."
---

# Codebase Explorer

Learn just enough of an existing repository to change it safely. Read selectively; do not read every file.

## Steps

1. **Outside first.** Read the README, the dependency file (`pyproject.toml`, `requirements.txt`, `package.json`, `pom.xml`, ...) and the top-level folder layout. Open other files only when a later step needs them.
2. **Pin down the run and test commands.** Find how the project runs and how it is tested. Run the existing tests once before any edit and record the baseline on the `Baseline` line of the `## Repository` section of `TASK_BRIEF.md` (if the file does not exist, create it from the template in `../task-router/SKILL.md` first): passed and failed counts, and the names of tests that already fail.
3. **Find the relevant code.** Search for the task's keywords (names, messages, routes, file names). Write the path from the entry point to the code you must change as a short `file:line` list.
4. **Declare the scope.** In the `## Repository` section of `TASK_BRIEF.md`, list the files you will change (`Change:`) and the ones you will leave alone (`Leave:`). Follow the existing style for naming, error handling and tests.

## Rules

- No refactoring or reformatting outside the task.
- Add or upgrade dependencies only when the task requires it.
- Tests that already failed in the baseline are not regressions. Leave them unless the task asks for them.
- For language-specific commands see `../tdd-automator/references/languages.md`.
