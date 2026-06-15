import io
import json
from pathlib import Path

from backend.sources.refresh_command_cli import run_primary_refresh_command_io
from backend.storage.summary_command_cli import run_load_storage_summary_command_io


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def run_load_payload(payload: object, *, database_path: str | Path | None = None):
    stdout = io.StringIO()
    exit_code = run_load_storage_summary_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
        database_path=database_path,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def seed_refresh_database(database_path: Path):
    stdout = io.StringIO()
    exit_code = run_primary_refresh_command_io(
        io.StringIO(
            json.dumps(
                {
                    "codex_jsonl_root": str(FIXTURE_ROOT / "codex"),
                    "claude_code_jsonl_root": str(FIXTURE_ROOT / "claude_code"),
                    "end_day_utc": "2026-06-14",
                    "started_at": "2026-06-14T00:00:00Z",
                }
            )
        ),
        stdout,
        database_path=database_path,
    )
    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert "error" not in payload
    assert database_path.exists()


def test_load_storage_summary_cli_reads_file_backed_refresh_database_without_paths(tmp_path):
    database_path = tmp_path / "usage.sqlite"
    seed_refresh_database(database_path)

    exit_code, text, payload = run_load_payload(
        {"end_day_utc": "2026-06-14"},
        database_path=database_path,
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert payload["summary"]["totals"]["total_tokens"] == 7570
    assert payload["generated_from"] == "backend.storage.summary_payload"
    assert payload["refresh_state"]["last_status"] == "succeeded"
    assert payload["refresh_state"]["successful_source_count"] == 2
    assert "refresh_results" not in payload
    assert str(database_path) not in text
    assert "experiments/fixtures" not in text
    assert "local_sources" not in text


def test_load_storage_summary_cli_missing_database_is_unavailable_without_creating_file(tmp_path):
    database_path = tmp_path / "missing" / "usage.sqlite"

    exit_code, text, payload = run_load_payload(
        {"end_day_utc": "2026-06-14"},
        database_path=database_path,
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "storage_summary_unavailable",
            "field": "database_path",
            "message": "storage summary database is unavailable",
        }
    }
    assert str(database_path) not in text
    assert not database_path.exists()
    assert not database_path.parent.exists()


def test_load_storage_summary_cli_ignores_request_database_path_without_internal_database(tmp_path):
    database_path = tmp_path / "usage.sqlite"

    exit_code, text, payload = run_load_payload(
        {
            "database_path": str(database_path),
            "end_day_utc": "2026-06-14",
        }
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_storage_summary_request"
    assert "unsupported storage summary fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert str(database_path) not in text
    assert not database_path.exists()


def test_load_storage_summary_cli_rejects_unknown_fields_when_connection_is_available(tmp_path):
    database_path = tmp_path / "usage.sqlite"
    seed_refresh_database(database_path)

    exit_code, text, payload = run_load_payload(
        {
            "database_path": str(database_path),
            "end_day_utc": "2026-06-14",
        },
        database_path=database_path,
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_storage_summary_request"
    assert "unsupported storage summary fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert str(database_path) not in text


def test_load_storage_summary_cli_rejects_invalid_end_day_without_paths(tmp_path):
    database_path = tmp_path / "usage.sqlite"
    seed_refresh_database(database_path)

    exit_code, text, payload = run_load_payload(
        {"end_day_utc": "2026-6-14"},
        database_path=database_path,
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_storage_summary_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
    assert str(database_path) not in text
