# Example: mock task to brief

Statement (mock): "Read `scores.csv` (columns `name,score`, up to 200,000 rows). Print the top 3 names by score, ties broken by name ascending, one per line. Time limit 2 s."

Resulting `TASK_BRIEF.md` (abridged):

```markdown
# Task Brief
Type: data

## Goal
Print the 3 highest-scoring names from scores.csv.

## Inputs / Outputs
- Input: scores.csv with header `name,score`
- Output: 3 lines on stdout, one name per line

## Constraints
- Up to 200,000 rows; 2 s time limit

## Facts vs assumptions
- FACT: "ties broken by name ascending"
- ASSUMPTION: scores may be non-integers (not stated); parse as float
- ASSUMPTION: with fewer than 3 rows, print all rows

## Skills
- tdd-automator: tie-breaking and short-file cases are easy to get wrong
- submission-validator: exact stdout format
```

`algorithm-optimizer` is not selected: sorting 200,000 rows is well within 2 s.
