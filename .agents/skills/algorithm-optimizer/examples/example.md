# Example: O(n^2) to O(n)

Mock task: count pairs `i < j` with `a[i] + a[j] == k`, `n <= 200,000`, 1 s.

Before (O(n^2), about 2e10 steps at n = 200,000, too slow):

```python
def count_pairs(a, k):
    return sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if a[i] + a[j] == k)
```

After (O(n) with a hash map of counts seen so far):

```python
from collections import Counter


def count_pairs(a, k):
    seen, total = Counter(), 0
    for x in a:
        total += seen[k - x]
        seen[x] += 1
    return total
```

The same tests pass before and after; the n = 200,000 case went from timing out to well under a second.
