# Example: mock repository task

Statement (mock): "In the given `shop` repository, make `GET /orders` accept a `status` query parameter that filters orders."

1. Outside first: the README says `uvicorn shop.main:app`; `pyproject.toml` lists FastAPI and pytest; top-level folders are `shop/` and `tests/`.
2. Baseline: `python -m pytest -q` -> `18 passed, 1 failed` (`test_refund_rounding` already fails). Recorded in `TASK_BRIEF.md`.
3. Relevant code:
   - `shop/main.py:12` includes `orders.router`
   - `shop/routes/orders.py:30` `list_orders()` handles `GET /orders`
   - `shop/repo.py:44` `fetch_orders()` builds the query
4. Scope in `TASK_BRIEF.md`:
   - change: `shop/routes/orders.py`, `shop/repo.py`, `tests/test_orders.py`
   - leave: `test_refund_rounding` and the refund code (outside the task)
