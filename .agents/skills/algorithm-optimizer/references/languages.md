# Performance notes by language

| Language | Notes |
|---|---|
| Python | Read input with `sys.stdin.buffer` or `sys.stdin.readline`; use `collections.deque`, `heapq`, `bisect`, `functools.lru_cache`; raise `sys.setrecursionlimit` or rewrite deep recursion as a loop; avoid string `+=` in loops (use `"".join`). |
| C++ | Compile with `-O2`; `std::ios::sync_with_stdio(false); std::cin.tie(nullptr);`; prefer `std::vector` over `std::list`; `unordered_map` can degrade on adversarial keys. |
| Java | `BufferedReader` and `StringBuilder` for I/O; avoid boxing in hot loops (`int[]` over `List<Integer>`). |
| JavaScript | Read all input at once (`fs.readFileSync(0)`); `Map`/`Set` for lookups; avoid `Array.prototype.shift` in loops (O(n)). |
