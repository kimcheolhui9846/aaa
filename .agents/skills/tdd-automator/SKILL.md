---
name: tdd-automator
description: "Use when implementing or fixing core logic whose results can be checked - writes failing tests first from the task's examples and relevant boundaries, then implements until they pass. Do NOT use for pure formatting, config, docs, or trivial one-line edits."
---

# TDD Automator

## Steps

1. Read `TASK_BRIEF.md` if it exists. List the behaviours the task actually checks.
2. Turn every example in the task statement into a test first. These are the most valuable tests.
3. Add boundary cases only when the input definition allows them:
   - empty or single-element input; minimum and maximum sizes and values
   - duplicates, already sorted or reverse sorted, negative numbers, zero
   - None / NaN / missing values only if the input format can contain them
   Skip cases the statement rules out.
4. Run the tests and confirm they fail for the expected reason (missing function or wrong result, not a typo).
5. Implement the smallest change that makes them pass. Run again.
6. On failure, read the assertion and fix the code. Change a test only if it contradicts the statement.
7. Keep the suite fast (about 10 s). Large-input timing belongs to the benchmark skill.

## Running tests

See `references/languages.md`. In Python prefer `python -m pytest -q`; if pytest is not available, a plain script with `assert` statements is fine.

## Reporting

- Give the exact command you ran and its result (`N passed`, or the failure).
- If tests could not run (no runner, no permission, missing dependency), say so and why.
- Never report a test as passing without running it.
