"""Worker tests PIPE-21."""

from backend.modules.pipeline.worker import main


def test_worker_bad_stage_returns_nonzero():
    rc = main(["--stage", "bad_stage_does_not_exist"])
    assert rc != 0


def test_worker_max_jobs_zero_returns_zero():
    # No jobs, max-jobs 0 should exit cleanly
    rc = main(["--stage", "ingest", "--max-jobs", "0"])
    assert rc == 0
