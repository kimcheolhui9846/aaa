# Test runners by language

| Language | Runner (preferred, then fallback) | Run command |
|---|---|---|
| Python | pytest, then a plain script with `assert` | `python -m pytest -q` / `python test_x.py` |
| C++ | separate test `main` using `<cassert>` | `g++ -std=c++17 -O2 -o test_x test_x.cpp && ./test_x` |
| Java | JUnit if the project already has it, else a `main` with checks | `javac *.java && java -ea TestMain` |
| JavaScript | built-in `node:test` | `node --test` |

- Python: if `python -m pytest` says "No module named pytest", use a plain script; install packages only if the task allows it.
- C++ and Java asserts are off with `-DNDEBUG` or without `-ea`; check the flags.
- Keep test inputs synthetic.
