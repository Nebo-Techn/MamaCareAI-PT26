# Tests

Automated tests for every module, run with `pytest`.

This is not optional scaffolding — it's part of the Definition of Done. A pull
request that adds or changes behavior in `modules/` without a matching test
change here does not get merged. "It worked when I ran it manually" is not
evidence; a test that fails when the code is wrong is.

Mirror the `modules/` structure: `tests/test_ingestion.py`,
`tests/test_rag.py`, etc. Runs automatically on every PR via
`.github/workflows/ci.yml`.

**Owner track:** everyone — you test your own module.
