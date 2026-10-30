---
name: task-router
description: "Use when starting a new non-trivial coding task or when requirements are unclear - writes goal, I/O, constraints and evaluation to TASK_BRIEF.md and picks the fewest other skills. Do NOT use for one-line fixes, follow-ups on a briefed task, or questions needing no code."
---

# Task Router

Turn the task statement into a short written brief, then choose the fewest skills that cover it.

## Steps

1. Read the whole task statement and list every provided file. Do not write solution code yet.
2. Extract, quoting the statement where possible:
   - **Goal**: one sentence.
   - **Inputs/outputs**: formats, file names and paths, encodings, exact output layout.
   - **Constraints**: language and version, allowed libraries, input size limits, time and memory limits.
   - **Evaluation**: how the result is judged (hidden tests, exact output match, performance, review).
3. Separate facts from assumptions. Anything the statement does not say is an assumption: mark it `ASSUMPTION` and choose the most conservative reading.
4. Classify the task as one of `algorithm`, `data`, `web-api`, `output-format`, `debugging`, `other`.
5. Select skills. Add a skill only when its condition holds:

   | Condition | Skill |
   |---|---|
   | Core logic with checkable inputs and outputs | `tdd-automator` |
   | Input sizes or time/memory limits are stated, or a naive approach would be too slow | `algorithm-optimizer` |
   | There is a deliverable (files, output format, run command) | `submission-validator`, before finishing |
   | The user wants the design explained | `implementation-review` (explicit `$implementation-review` only) |
   | Measured slowness needs profiling | `benchmark` (explicit `$benchmark` only) |

6. Write `TASK_BRIEF.md` in the workspace root with the template below. Keep it under 40 lines.
7. Re-read `TASK_BRIEF.md` when the conversation gets long and before declaring the task done.

## TASK_BRIEF.md template

```markdown
# Task Brief
Type: <algorithm|data|web-api|output-format|debugging|other>

## Goal
<one sentence>

## Inputs / Outputs
- <format, files, paths, exact layout>

## Constraints
- <language, libraries, sizes, limits>

## Evaluation
- <how the result is judged>

## Facts vs assumptions
- FACT: <quoted from the statement>
- ASSUMPTION: <what you assumed and why>

## Risks
- <edge cases, ambiguities, performance traps>

## Skills
- <skill>: <why it is needed>
```

## Rules

- If an ambiguity would change the output, ask the user before building.
- Keep the brief inside the workspace. Never send task content anywhere else.
