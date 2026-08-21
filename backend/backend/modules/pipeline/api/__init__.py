"""
HTTP API for the pipeline — FastAPI routers.

Two surfaces, deliberately separate:

  routes_pipeline.py  submission and status. Internal/admin.
  routes_review.py    the human review UI's backend (PDF 3.6).

THESE ROUTERS ARE THIN. Every handler validates input, calls one service
method, and shapes the response. No workflow logic, no database queries, no
state transitions in a route handler — all of that lives in `services/` so it
is reachable from the CLI, testable without HTTP, and impossible to bypass.

If a route handler grows past ~15 lines, the logic in it belongs in a service.

Mounted by `backend/main.py` alongside the existing /chat and /health routers.
"""
