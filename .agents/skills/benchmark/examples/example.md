# Example: before and after

Mock: `count_pairs` from the algorithm-optimizer example, n = 200,000, seed 0.

| Version | Input size | Best of 5 (s) | Peak memory |
|---|---|---|---|
| nested loops | 2,000 | 0.21 | 0.1 MB |
| nested loops | 200,000 | stopped after 60 s | - |
| Counter | 200,000 | 0.05 | 12 MB |

Noise: laptop on battery; numbers vary by about 10% between runs.
