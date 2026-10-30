---
name: systematic-debugging
description: "Use when a test fails, output is wrong, or the program crashes and the cause is not yet known - finds the root cause before changing code. Do NOT use when the cause is already obvious, or for slowness (use algorithm-optimizer)."
---

# Systematic Debugging

Find the root cause before changing code. Guessing wastes time and tokens.

## Steps

1. **Reproduce.** Find the shortest command that shows the failure and write it down. Read the whole error message and stack trace.
2. **Narrow down.** Compare with what last worked (`git diff`, the last passing run) and with similar code that works. List the differences. Trace the bad value backwards to where it first appears.
3. **One hypothesis, smallest check.** Write "Y happens because X" in one sentence. Check only that, with the smallest change or a temporary print. If it is wrong, go back to step 2.
4. **Fix.** Add a test that reproduces the failure (as in `tdd-automator`), fix that one cause, then run the full test suite.
5. **Record.** Append `- <cause> -> <fix> -> <evidence>` to the Decision log in `TASK_BRIEF.md`.

## Rules

- Change no code before you have a root-cause hypothesis, except temporary prints in step 3.
- After three failed fixes, stop. Report the hypotheses tried and their evidence to the user instead of trying a fourth.
- Remove temporary prints and debug flags when done.
- For language-specific test and debug commands see `../tdd-automator/references/languages.md`.

---

Adapted from obra/superpowers (MIT). See THIRD_PARTY_NOTICES.md in the kit repository.
