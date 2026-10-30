---
name: submission-validator
description: "Use right before finishing - checks the result against every requirement in TASK_BRIEF.md or the statement, file names and formats, leftover debug output, and runs tests and linters with evidence. Do NOT use mid-implementation or when there is no deliverable."
---

# Submission Validator

## Steps

1. Build a checklist with one row per requirement from `TASK_BRIEF.md` (or the statement if there is no brief).
2. Run the automated checks and record the exact command and result for each:
   - required files exist at the required paths with the exact names
   - the program runs with the stated command, and its output on the statement's examples matches the stated format exactly (whitespace, line endings, ordering)
   - tests pass; the linter passes if one is available
   - no leftover debug output or markers (see `references/languages.md` for search commands)
   - no hard-coded absolute paths from this machine; no unused heavy dependencies
3. List the checks only a human can do (judgement calls, visual checks, the exam's own submission step) as MANUAL. Do not mark them as passed.
4. Output a table: `Requirement | Check | Evidence | Result` with Result one of PASS, FAIL, MANUAL.
5. If anything FAILs, fix it and re-run only the affected checks, then re-print the table.

## Rules

- Never click submission buttons or operate a browser. The human submits.
- Never report PASS without the command output that shows it.
