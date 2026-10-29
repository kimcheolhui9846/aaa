# Timing by language

| Language | Wall time | Profiling | Memory |
|---|---|---|---|
| Python | `timeit.repeat` (best of 5) | `cProfile` + `pstats` | `tracemalloc` |
| C++ | `std::chrono::steady_clock` around the call, build with `-O2` | `perf` or `gprof` if installed | `/usr/bin/time -v` (Linux) |
| Java | `System.nanoTime()` after a warm-up run | JDK Flight Recorder (`-XX:StartFlightRecording`) if allowed | `Runtime.getRuntime()` totals |
| JavaScript | `performance.now()` | `node --cpu-prof` | `process.memoryUsage()` |

Use the same machine, input, seed and build flags for before and after.
