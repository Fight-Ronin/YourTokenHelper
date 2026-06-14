import io
import json
import sqlite3
from pathlib import Path

from backend.sources.refresh_command_cli import run_primary_refresh_command_io
from backend.storage import connect_database, initialize_schema, query_daily_summary


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def run_cli_payload(
    payload: object,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
):
    stdout = io.StringIO()
    exit_code = run_primary_refresh_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
        connection=connection,
        database_path=database_path,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def test_primary_refresh_command_cli_returns_fixture_success_without_paths():
    exit_code, text, payload = run_cli_payload(
        {
            "codex_jsonl_root": str(FIXTURE_ROOT / "codex"),
            "claude_code_jsonl_root": str(FIXTURE_ROOT / "claude_code"),
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z",
        },
        connection=memory_connection(),
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert "experiments/fixtures" not in text
    assert "local_sources" not in text


def test_primary_refresh_command_cli_can_use_file_backed_database(tmp_path):
    database_path = tmp_path / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "codex_jsonl_root": str(FIXTURE_ROOT / "codex"),
            "claude_code_jsonl_root": str(FIXTURE_ROOT / "claude_code"),
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z",
        },
        database_path=database_path,
    )

    assert exit_code == 0
    assert "error" not in payload
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert str(database_path) not in text

    connection = connect_database(database_path)
    try:
        summary = query_daily_summary(connection, "2026-06-14")
    finally:
        connection.close()
    assert summary.totals.total_tokens == 7570


def test_primary_refresh_command_cli_does_not_accept_database_path_in_request(tmp_path):
    database_path = tmp_path / "must-not-be-created.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "database_path": str(database_path),
            "end_day_utc": "2026-06-14",
        }
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_refresh_request"
    assert "unsupported refresh command fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert str(database_path) not in text
    assert not database_path.exists()


def test_primary_refresh_command_cli_redacts_database_open_errors(tmp_path):
    database_path = tmp_path / "missing" / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "end_day_utc": "2026-06-14",
        },
        database_path=database_path,
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "field": "database_path",
            "message": "refresh database could not be opened",
        }
    }
    assert str(database_path) not in text


def test_primary_refresh_command_cli_returns_structured_error_without_echoing_roots():
    exit_code, text, payload = run_cli_payload(
        {
            "codex_jsonl_root": "C:/Users/example/secret/codex",
            "end_day_utc": "2026-6-14",
        }
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text
    assert "codex" not in text


def test_primary_refresh_command_cli_rejects_non_json_stdin():
    stdout = io.StringIO()
    exit_code = run_primary_refresh_command_io(io.StringIO("not-json"), stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "message": "refresh request must be valid JSON",
        }
    }
