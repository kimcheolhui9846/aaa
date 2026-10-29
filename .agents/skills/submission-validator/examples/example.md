# Example: validation table

Mock task: "Write `solution.py` that reads `input.txt` and writes `output.txt` with one integer per line."

| Requirement | Check | Evidence | Result |
|---|---|---|---|
| File named `solution.py` at the root | `ls solution.py` | file listed | PASS |
| Writes `output.txt`, one integer per line | `python solution.py && python -c "[int(l) for l in open('output.txt')]"` | exit 0, no ValueError | PASS |
| Matches the statement example | `python solution.py` on the example, then `diff output.txt expected.txt` | no diff | PASS |
| No debug prints | `grep -n "print(" solution.py` | 1 hit, line 40 writes the result | PASS |
| Tests pass | `python -m pytest -q` | `6 passed` | PASS |
| Submitted through the exam page | human step | - | MANUAL |
