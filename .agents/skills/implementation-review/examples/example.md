# Example: review of the mock pair-count solution

## How it works
- One pass; for each x, add how many earlier values equal k - x.

## Key decisions
- Counter of seen values: O(1) lookups; sorting with two pointers would be O(n log n) and needs extra care for duplicates.

## Why it is correct
- Each pair (i, j) with i < j is counted exactly once, when j is visited. Tests cover duplicates, an empty list and no pairs.

## Complexity
- Time: O(n)  Space: O(n)  (n = len(a))

## Limits
- Memory grows with the number of distinct values.
