import io
import json
from pathlib import Path

from backend.sources.openai_admin_command_cli import run_openai_admin_sync_command_io
from backend.storage import connect_database, query_cost_total_usd, query_rolling_7d_summary


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_probe_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def run_cli_payload(payload: object, *, database_path: str | Path | None = None):
    stdout = io.StringIO()
    exit_code = run_openai_admin_sync_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
        database_path=database_path,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def test_openai_admin_sync_command_cli_can_use_file_backed_database(tmp_path):
    database_path = tmp_path / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T00:00:00Z",
            "payload": fixture_payload(),
        },
        database_path=database_path,
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert "error" not in payload
    assert payload["sync_result"]["usage_events_seen"] == 3
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 43100
    assert str(database_path) not in text
    assert str(FIXTURE_PATH) not in text
    assert "key_fixture" not in text
    assert "proj_fixture" not in text

    connection = connect_database(database_path)
    try:
        summary = query_rolling_7d_summary(connection, "2026-06-13")
        cost_total = query_cost_total_usd(connection, "2026-06-12", "2026-06-13")
    finally:
        connection.close()
    assert summary.event_count == 109
    assert summary.totals.total_tokens == 43100
    assert cost_total == 1.03


def test_openai_admin_sync_command_cli_does_not_accept_database_path_in_request(tmp_path):
    database_path = tmp_path / "must-not-be-created.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "database_path": str(database_path),
            "end_day_utc": "2026-06-13",
            "payload": fixture_payload(),
        }
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_openai_admin_sync_request"
    assert "unsupported OpenAI Admin sync fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert str(database_path) not in text
    assert "key_fixture" not in text
    assert not database_path.exists()


def test_openai_admin_sync_command_cli_redacts_database_open_errors(tmp_path):
    database_path = tmp_path / "missing" / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "end_day_utc": "2026-06-13",
            "payload": fixture_payload(),
        },
        database_path=database_path,
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "field": "database_path",
            "message": "OpenAI Admin sync database could not be opened",
        }
    }
    assert str(database_path) not in text
    assert "key_fixture" not in text


def test_openai_admin_sync_command_cli_rejects_non_json_stdin():
    stdout = io.StringIO()
    exit_code = run_openai_admin_sync_command_io(io.StringIO("not-json"), stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "message": "OpenAI Admin sync request must be valid JSON",
        }
    }
