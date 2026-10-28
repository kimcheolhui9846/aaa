# Example: tests first for a mock task

Mock task: `longest_run(xs)` returns the length of the longest block of equal adjacent values; `0 <= len(xs) <= 100000`.

```python
# test_longest_run.py - written before solution.py exists
from solution import longest_run


def test_statement_example():
    assert longest_run([1, 1, 2, 2, 2, 1]) == 3


def test_empty():
    assert longest_run([]) == 0


def test_single():
    assert longest_run([7]) == 1


def test_all_equal():
    assert longest_run([5] * 1000) == 1000


def test_run_at_end():
    assert longest_run([1, 2, 3, 3]) == 2
```

NaN is not tested: the input is a list of ints.

`python -m pytest -q test_longest_run.py` fails with `ImportError` before `solution.py` exists and passes after it is implemented.
