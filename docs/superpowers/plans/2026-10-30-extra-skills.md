# Extra Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `systematic-debugging` and `codebase-explorer` skills to the kit, extend `task-router` and `submission-validator`, and keep the description budget at or under 2000 characters.

**Architecture:** Skills are plain Markdown folders under `.agents/skills/<name>/`. The installer copies every skill listed in `profiles/core.json` (other profiles inherit from it), so no Python code under `kit/` changes. Tests in `tests/test_skills.py` and `tests/test_profiles.py` hold the skill list and the content checks.

**Tech Stack:** Markdown, JSON, Python 3.12 + pytest + ruff via `uv`.

Spec: `docs/superpowers/specs/2026-10-30-extra-skills-design.md`

## Global Constraints

- Total of all skill `description` values ≤ 2000 characters (`test_total_description_budget`).
- Each description is one line in double quotes, contains no other `"`, and contains `Do NOT use`.
- `benchmark` and `implementation-review` descriptions keep the prefix `Use only when explicitly invoked`.
- New skills get no `agents/openai.yaml` (implicit invocation allowed) and are not added to `required_skills`.
- SKILL.md and examples are in English; README and docs are in Korean.
- Skills hold procedure only: no solution templates, no Codex install/update instructions.
- Upstream source: `https://github.com/obra/superpowers`, commit `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`, MIT, `Copyright (c) 2025 Jesse Vincent`.
- No `git push`. Commit with the repo's configured identity, no AI co-author trailers.

All commands run from the repo root `D:\aaa\aaa` in Git Bash.

---

### Task 1: `systematic-debugging` skill and third-party notice

**Files:**
- Create: `.agents/skills/systematic-debugging/SKILL.md`
- Create: `.agents/skills/systematic-debugging/examples/example.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Modify: `profiles/core.json` (`skills` list)
- Test: `tests/test_skills.py`, `tests/test_profiles.py`

**Interfaces:**
- Produces: list name `EXTRA` in `tests/test_skills.py` (new skills beyond the original six); Task 2 appends to it.

- [ ] **Step 1: Write the failing tests**

In `tests/test_skills.py`, replace

```python
ALL = CORE + ["implementation-review", "benchmark"]
```

with

```python
EXTRA = ["systematic-debugging"]
ALL = CORE + ["implementation-review", "benchmark"] + EXTRA
```

and append at the end of the file:

```python
@pytest.mark.parametrize("name", EXTRA)
def test_extra_skill_has_example(kit_root, name):
    assert list((kit_root / ".agents" / "skills" / name / "examples").glob("*.md"))


@pytest.mark.parametrize("name", EXTRA)
def test_extra_skill_description_is_one_quoted_line(kit_root, name):
    text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("description:"))
    assert line.startswith('description: "') and line.endswith('"')
    assert line.count('"') == 2


@pytest.mark.parametrize("name", EXTRA)
def test_extra_skill_is_implicit(kit_root, name):
    assert not (kit_root / ".agents" / "skills" / name / "agents" / "openai.yaml").exists()


def test_debugging_skill_credits_source(kit_root):
    text = (kit_root / ".agents/skills/systematic-debugging/SKILL.md").read_text(encoding="utf-8")
    assert "Adapted from obra/superpowers (MIT)" in text


def test_third_party_notices(kit_root):
    text = (kit_root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "https://github.com/obra/superpowers" in text
    assert "2ce8aa15d05bd57213e6f746f953aafb7ded7a8b" in text
    assert "MIT License" in text
    assert "Copyright (c) 2025 Jesse Vincent" in text
```

In `tests/test_profiles.py`, add `"systematic-debugging",` as the last entry of `ALL_SKILLS` (after `"benchmark",`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_skills.py tests/test_profiles.py`
Expected: FAIL — `SKILL.md missing` for `systematic-debugging`, missing `THIRD_PARTY_NOTICES.md`, profile skill list mismatch.

- [ ] **Step 3: Create `.agents/skills/systematic-debugging/SKILL.md`**

```markdown
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
```

- [ ] **Step 4: Create `.agents/skills/systematic-debugging/examples/example.md`**

```markdown
# Example: mock failing test

Failure (mock): `test_top3_ties` fails - expected `['ann', 'bob', 'cat']`, got `['bob', 'ann', 'cat']`.

1. Reproduce: `python -m pytest -q tests/test_top3.py::test_top3_ties` fails the same way on every run.
2. Narrow down: the test passed before the last edit. `git diff` shows the sort key changed from `(-score, name)` to `-score`. Ann and Bob have the same score.
3. Hypothesis: "The order is wrong because the sort key lost the name tie-breaker." Check: print the keys for ann and bob -> both `-90.0`. Confirmed.
4. Fix: restore the key `(-score, name)`. `test_top3_ties` passes; the full suite gives `12 passed`.
5. Decision log line:

   `- sort key lost name tie-breaker -> restored (-score, name) -> test_top3_ties passes, 12 passed`
```

- [ ] **Step 5: Create `THIRD_PARTY_NOTICES.md`**

````markdown
# Third-party notices

This file stays in the kit repository. The installer does not copy it into workspaces.

## obra/superpowers

- Repository: https://github.com/obra/superpowers
- Commit: 2ce8aa15d05bd57213e6f746f953aafb7ded7a8b
- Used:
  - `skills/systematic-debugging/SKILL.md` -> `.agents/skills/systematic-debugging/`, shortened and adapted for Codex and the exam rules (supporting files and references to other superpowers skills removed).
  - `skills/verification-before-completion/SKILL.md` -> its rules only, folded into `.agents/skills/submission-validator/SKILL.md` (fresh evidence only; checks that did not run are `NOT RUN`, never `PASS`).

```text
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
````

Then check the license text against upstream (whitespace-insensitive):

Run: `D=$(mktemp -d); curl -s https://raw.githubusercontent.com/obra/superpowers/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/LICENSE | tr -s ' \n' ' ' > "$D/up.txt"; sed -n '/^MIT License/,/^SOFTWARE\.$/p' THIRD_PARTY_NOTICES.md | tr -s ' \n' ' ' > "$D/ours.txt"; diff "$D/up.txt" "$D/ours.txt" && echo SAME`
Expected: `SAME` (a trailing-space-only difference is acceptable; any word difference must be fixed to match upstream).

- [ ] **Step 6: Add the skill to `profiles/core.json`**

In the `skills` array, add `"systematic-debugging"` after `"benchmark"`:

```json
  "skills": [
    "task-router",
    "tdd-automator",
    "algorithm-optimizer",
    "submission-validator",
    "implementation-review",
    "benchmark",
    "systematic-debugging"
  ],
```

Leave `required_skills` unchanged.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_skills.py tests/test_profiles.py tests/test_verify.py`
Expected: all pass. (Description total is now 1747 + 227 = 1974, under 2000.)

- [ ] **Step 8: Commit**

```bash
git add .agents/skills/systematic-debugging THIRD_PARTY_NOTICES.md profiles/core.json tests/test_skills.py tests/test_profiles.py
git commit -m "feat: add systematic-debugging skill adapted from superpowers"
```

---

### Task 2: `codebase-explorer` skill and description trimming

**Files:**
- Create: `.agents/skills/codebase-explorer/SKILL.md`
- Create: `.agents/skills/codebase-explorer/examples/example.md`
- Modify: `description:` line of `.agents/skills/{task-router,tdd-automator,algorithm-optimizer,submission-validator,benchmark,implementation-review,systematic-debugging}/SKILL.md` (only `systematic-debugging` is already final; leave it)
- Modify: `profiles/core.json` (`skills`, `description`)
- Test: `tests/test_skills.py`, `tests/test_profiles.py`

**Interfaces:**
- Consumes: `EXTRA` list from Task 1.

- [ ] **Step 1: Write the failing tests**

In `tests/test_skills.py` change `EXTRA` to:

```python
EXTRA = ["systematic-debugging", "codebase-explorer"]
```

In `tests/test_profiles.py` add `"codebase-explorer",` as the last entry of `ALL_SKILLS`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_skills.py tests/test_profiles.py`
Expected: FAIL — `codebase-explorer: SKILL.md missing`, folder/profile list mismatch.

- [ ] **Step 3: Create `.agents/skills/codebase-explorer/SKILL.md`**

```markdown
---
name: codebase-explorer
description: "Use when the task gives an existing repository to modify or extend - maps entry points, build and test commands and the code relevant to the task before any edit. Do NOT use for tasks that start from an empty workspace or a single file."
---

# Codebase Explorer

Learn just enough of an existing repository to change it safely. Read selectively; do not read every file.

## Steps

1. **Outside first.** Read the README, the dependency file (`pyproject.toml`, `requirements.txt`, `package.json`, `pom.xml`, ...) and the top-level folder layout. Open other files only when a later step needs them.
2. **Fix the run and test commands.** Find how the project runs and how it is tested. Run the existing tests once before any edit and record the baseline in `TASK_BRIEF.md`: passed and failed counts, and the names of tests that already fail.
3. **Find the relevant code.** Search for the task's keywords (names, messages, routes, file names). Write the path from the entry point to the code you must change as a short `file:line` list.
4. **Declare the scope.** In `TASK_BRIEF.md`, list the files you will change and the ones you will leave alone. Follow the existing style for naming, error handling and tests.

## Rules

- No refactoring or reformatting outside the task.
- Add or upgrade dependencies only when the task requires it.
- Tests that already failed in the baseline are not regressions. Leave them unless the task asks for them.
- For language-specific commands see `../tdd-automator/references/languages.md`.
```

- [ ] **Step 4: Create `.agents/skills/codebase-explorer/examples/example.md`**

```markdown
# Example: mock repository task

Statement (mock): "In the given `shop` repository, make `GET /orders` accept a `status` query parameter that filters orders."

1. Outside first: the README says `uvicorn shop.main:app`; `pyproject.toml` lists FastAPI and pytest; top-level folders are `shop/` and `tests/`.
2. Baseline: `python -m pytest -q` -> `18 passed, 1 failed` (`test_refund_rounding` already fails). Recorded in `TASK_BRIEF.md`.
3. Relevant code:
   - `shop/main.py:12` includes `orders.router`
   - `shop/routes/orders.py:30` `list_orders()` handles `GET /orders`
   - `shop/repo.py:44` `fetch_orders()` builds the query
4. Scope in `TASK_BRIEF.md`:
   - change: `shop/routes/orders.py`, `shop/repo.py`, `tests/test_orders.py`
   - leave: `test_refund_rounding` and the refund code (outside the task)
```

- [ ] **Step 5: Add the skill to `profiles/core.json`**

Add `"codebase-explorer"` after `"systematic-debugging"` in `skills`, and change `description` to:

```json
  "description": "AGENTS.md and the eight kit skills. Installs no tools and no MCP servers.",
```

- [ ] **Step 6: Run the budget test to see it fail**

Run: `uv run pytest -q tests/test_skills.py::test_total_description_budget`
Expected: FAIL with `assert 2210 <= 2000` (1974 + 236).

- [ ] **Step 7: Replace the six existing `description:` lines**

Replace only the `description:` line in each file with exactly:

`.agents/skills/task-router/SKILL.md`:
```
description: "Use when starting a new non-trivial coding task or when requirements are unclear - writes goal, I/O, constraints and evaluation to TASK_BRIEF.md and picks the fewest other skills. Do NOT use for one-line fixes, follow-ups on a briefed task, or questions needing no code."
```

`.agents/skills/tdd-automator/SKILL.md`:
```
description: "Use when implementing or fixing checkable core logic - writes failing tests from the task's examples and relevant boundaries first, then implements until they pass. Do NOT use for formatting, config, docs, or trivial one-line edits."
```

`.agents/skills/algorithm-optimizer/SKILL.md`:
```
description: "Use when the task states input sizes or time/memory limits, or a working solution is too slow - estimates allowed complexity, finds the bottleneck, compares better algorithms and re-runs tests. Do NOT use when inputs are small and limits are already met."
```

`.agents/skills/submission-validator/SKILL.md`:
```
description: "Use right before finishing - checks the result against every requirement in TASK_BRIEF.md or the statement, file names and formats, leftover debug output, and runs tests and linters with evidence. Do NOT use mid-implementation or when there is no deliverable."
```

`.agents/skills/benchmark/SKILL.md`:
```
description: "Use only when explicitly invoked as $benchmark - measures runtime or memory on synthetic inputs (timeit, cProfile, tracemalloc) and compares before and after under the same conditions. Do NOT use automatically or when tests show it is fast enough."
```

`.agents/skills/implementation-review/SKILL.md`:
```
description: "Use only when explicitly invoked as $implementation-review - explains why the current solution works: key branches, data structures, correctness, complexity and limits. Do NOT use automatically, and never during the written-answer phase."
```

Measured lengths: 270, 232, 254, 259, 247, 237; with 227 + 236 the total is 1962.

- [ ] **Step 8: Run the whole skill and profile suites**

Run: `uv run pytest -q tests/test_skills.py tests/test_profiles.py tests/test_verify.py`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add .agents/skills profiles/core.json tests/test_skills.py tests/test_profiles.py
git commit -m "feat: add codebase-explorer skill and trim descriptions to fit the budget"
```

---

### Task 3: Extend `task-router` and `submission-validator`

**Files:**
- Modify: `.agents/skills/task-router/SKILL.md`
- Modify: `.agents/skills/submission-validator/SKILL.md`
- Modify: `.agents/skills/submission-validator/examples/example.md`
- Test: `tests/test_skills.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_skills.py`:

```python
def test_task_router_routes_new_skills(kit_root):
    text = (kit_root / ".agents/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    for needle in ("`codebase-explorer`", "`systematic-debugging`", "## Plan", "## Decision log"):
        assert needle in text


def test_submission_validator_has_not_run(kit_root):
    text = (kit_root / ".agents/skills/submission-validator/SKILL.md").read_text(encoding="utf-8")
    assert "NOT RUN" in text
    assert "this validation pass" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest -q tests/test_skills.py -k "routes_new_skills or not_run"`
Expected: 2 FAIL.

- [ ] **Step 3: Edit `task-router/SKILL.md`**

(a) In the step 5 table, after the `algorithm-optimizer` row, insert:

```markdown
   | The task gives an existing repository to modify or extend | `codebase-explorer`, before any edit |
   | A test fails or the program misbehaves and the cause is unknown | `systematic-debugging` |
```

(b) Replace step 6 and step 7 with:

```markdown
6. Write `TASK_BRIEF.md` in the workspace root with the template below. Keep it under 40 lines, not counting the Decision log.
7. Re-read `TASK_BRIEF.md` when the conversation gets long and before declaring the task done. Append one Decision log line for each non-obvious decision.
```

(c) In the template, after the `## Skills` block (`- <skill>: <why it is needed>`), add:

```markdown

## Plan
1. <first step>
2. <next step>
<3 to 5 steps in order>

## Decision log
- <what> -> <why> -> <evidence>
```

- [ ] **Step 4: Edit `submission-validator/SKILL.md`**

Replace step 4 with:

```markdown
4. Output a table: `Requirement | Check | Evidence | Result` with Result one of PASS, FAIL, MANUAL, NOT RUN.
```

Replace the `## Rules` section with:

```markdown
## Rules

- Never click submission buttons or operate a browser. The human submits.
- Evidence must come from commands run in this validation pass. Do not reuse results from earlier in the session.
- A check that could not run is NOT RUN, with the reason. Never report PASS without the command output that shows it.
```

- [ ] **Step 5: Add a NOT RUN row to `submission-validator/examples/example.md`**

Insert before the `| Submitted through the exam page | ...` row:

```markdown
| Linter passes | `ruff check .` | `ruff: command not found` | NOT RUN |
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest -q tests/test_skills.py`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/task-router .agents/skills/submission-validator tests/test_skills.py
git commit -m "feat: route new skills from task-router and add NOT RUN to submission-validator"
```

---

### Task 4: Docs sync and end-to-end verification

**Files:**
- Modify: `README.md` (line 5 "Skill 6개", line 77 "six")
- Modify: `docs/TEST_REPORT.md` (line 23 "Skill 6개")
- Regenerate: `docs/examples/*.log`

- [ ] **Step 1: Update README**

- Line 5: `Skill 6개(` → `Skill 8개(`.
- Line 77: `AGENTS.md and the six kit skills.` → `AGENTS.md and the eight kit skills.`

Check: `grep -n "6개\|six" README.md` shows no remaining skill-count hits.

- [ ] **Step 2: Update `docs/TEST_REPORT.md` line 23**

Replace with:

```markdown
- Codex가 Skill 8개를 실제로 로드하는지(`/skills`에 `systematic-debugging`, `codebase-explorer` 포함), `implementation-review`와 `benchmark`가 명시 호출 전용으로 표시되는지: 사용자의 대화형 확인 필요
```

- [ ] **Step 3: Regenerate example logs**

Run: `uv run python devtools/make_examples.py && git diff --stat docs/examples`
Expected: logs change only where skill lists or file counts appear. Inspect `git diff docs/examples` and confirm the new lines mention `systematic-debugging` / `codebase-explorer` and nothing else unrelated changed.

- [ ] **Step 4: Full test suite and linters**

Run: `uv run pytest -q`
Expected: all pass (previous baseline `300 passed, 1 skipped`; the count rises by the new tests).

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors.

- [ ] **Step 5: End-to-end install into an empty folder**

Run:

```bash
T=$(mktemp -d) && uv run python -I run_kit.py --target "$T" --profile core; echo "exit=$?"; ls "$T/.agents/skills"
```

Expected: report shows `Status: READY`, `exit=0`, and eight folders: `algorithm-optimizer benchmark codebase-explorer implementation-review submission-validator systematic-debugging task-router tdd-automator`. `THIRD_PARTY_NOTICES.md` is not in `$T`.

- [ ] **Step 6: Record results in `docs/TEST_REPORT.md`**

Add a row to the automated results table with the actual `pytest` summary line and date `2026-10-30`, and a line noting the e2e install result. Use only the real output from Steps 4 and 5.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/TEST_REPORT.md docs/examples
git commit -m "docs: sync skill count, example logs and test report for eight skills"
```

Do not push. Merging to `main` is the user's call (installs pull from `main`).
