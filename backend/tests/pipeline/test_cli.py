"""CLI tests PIPE-21 submit/status."""


from backend.modules.pipeline.cli import main


def test_cli_submit_prints_id(capsys):
    rc = main(["submit", "--url", "https://example.org/guide.pdf", "--type", "pdf"])
    assert rc == 0
    out = capsys.readouterr().out
    assert len(out.strip()) > 0  # resource_id


def test_cli_status_not_found():
    rc = main(["status", "--resource-id", "does-not-exist-123"])
    assert rc != 0


def test_cli_requeue_stub():
    rc = main(["requeue", "--stage", "translate"])
    assert rc == 2
