# Example: mock failing test

Failure (mock): `test_top3_ties` fails - expected `['ann', 'bob', 'cat']`, got `['bob', 'ann', 'cat']`.

1. Reproduce: `python -m pytest -q tests/test_top3.py::test_top3_ties` fails the same way on every run.
2. Narrow down: the test passed before the last edit. `git diff` shows the sort key changed from `(-score, name)` to `-score`. Ann and Bob have the same score.
3. Hypothesis: "The order is wrong because the sort key lost the name tie-breaker." Check: print the keys for ann and bob -> both `-90.0`. Confirmed.
4. Fix: restore the key `(-score, name)`. `test_top3_ties` passes; the full suite gives `12 passed`.
5. Decision log line:

   `- sort key lost name tie-breaker -> restored (-score, name) -> test_top3_ties passes, 12 passed`
