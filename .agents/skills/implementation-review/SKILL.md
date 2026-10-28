---
name: implementation-review
description: "Use only when explicitly invoked as $implementation-review - summarizes why the current solution works: key branches, data structure choices, correctness argument, complexity and limits, for the implementer's own understanding. Do NOT use automatically, and never during the written-answer phase."
---

# Implementation Review

Explain the solution so the implementer understands it. This is explanation only; it does not change behaviour.

## Steps

1. Read the solution and `TASK_BRIEF.md` if present.
2. Write the summary with this template, at most 25 lines:

```markdown
## How it works
- <the core idea in 1-2 lines>

## Key decisions
- <branch or data structure>: <why, and what the alternative would cost>

## Why it is correct
- <invariant or argument; mention the boundary cases covered by tests>

## Complexity
- Time: O(...)  Space: O(...)  (n = ...)

## Limits
- <inputs or situations where it would fail or slow down>
```

3. Add comments only to functions that are hard to follow, one or two lines each. Do not comment every line.

## Rules

- The written-answer phase of the exam forbids AI help. Stop using this skill and all AI assistance before it starts. Never draft, paste or submit written answers.
