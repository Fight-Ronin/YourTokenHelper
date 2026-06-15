import io
import json
from pathlib import Path

from backend.sources.manual_allowance_command_cli import run_manual_allowance_command_io
from backend.storage import connect_database, query_allowance_windows


def run_cli_payload(payload: object, *, database_path: str | Path | None = None):
    stdout = io.StringIO()
    exit_code = run_manual_allowance_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
        database_path=database_path,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def manual_payload(**overrides):
    payload = {
        "end_day_utc": "2026-06-14",
        "source_kind": "claude_code",
        "unit": "tokens",
        "limit_amount": 200000,
        "reset_at": "2026-06-21T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_manual_allowance_command_cli_can_use_file_backed_database(tmp_path):
    database_path = tmp_path / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        manual_payload(),
        database_path=database_path,
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert "error" not in payload
    assert payload["allowance_window"]["source_id"] == "claude_code:manual_allowance"
    assert str(database_path) not in text

    connection = connect_database(database_path)
    try:
        windows = query_allowance_windows(connection)
    finally:
        connection.close()
    assert len(windows) == 1
    assert windows[0].source_kind == "claude_code"
    assert windows[0].limit_amount == 200000


def test_manual_allowance_command_cli_does_not_accept_database_path_in_request(tmp_path):
    database_path = tmp_path / "must-not-be-created.sqlite"

    exit_code, text, payload = run_cli_payload(
        manual_payload(database_path=str(database_path))
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_manual_allowance_request"
    assert "unsupported manual allowance fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert str(database_path) not in text
    assert not database_path.exists()


def test_manual_allowance_command_cli_redacts_database_open_errors(tmp_path):
    database_path = tmp_path / "missing" / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        manual_payload(),
        database_path=database_path,
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "manual_allowance_unavailable",
            "field": "database_path",
            "message": "manual allowance database could not be opened",
        }
    }
    assert str(database_path) not in text


def test_manual_allowance_command_cli_rejects_non_json_stdin():
    stdout = io.StringIO()
    exit_code = run_manual_allowance_command_io(io.StringIO("not-json"), stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "message": "manual allowance request must be valid JSON",
        }
    }
