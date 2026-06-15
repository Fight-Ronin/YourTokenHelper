import io
import json
import os
from pathlib import Path

from backend.sidecar_cli import run_sidecar_command_io
from backend.sources import OPENAI_ADMIN_KEY_ENV_VAR
from backend.sources.api_provider_billing_sync_commands import (
    SYNC_API_PROVIDER_BILLING_COMMAND_NAME,
)
from backend.sources.commands import PRIMARY_REFRESH_COMMAND_NAME
from backend.sources.manual_allowance_commands import SAVE_MANUAL_ALLOWANCE_COMMAND_NAME
from backend.storage import connect_database, query_allowance_windows, query_daily_summary
from backend.storage.summary_command_cli import LOAD_STORAGE_SUMMARY_COMMAND_NAME


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")
REFRESH_DATABASE_PATH_ENV_VAR = "YTH_REFRESH_DATABASE_PATH"


def run_sidecar_payload(command_name: str, payload: object):
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run_sidecar_command_io(
        ["yth-backend", command_name],
        io.StringIO(json.dumps(payload)),
        stdout,
        stderr,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue(), json.loads(stdout.getvalue())


def test_sidecar_refresh_command_uses_database_path_from_env_without_paths(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "usage.sqlite"
    monkeypatch.setenv(REFRESH_DATABASE_PATH_ENV_VAR, str(database_path))

    exit_code, text, stderr, payload = run_sidecar_payload(
        PRIMARY_REFRESH_COMMAND_NAME,
        {
            "codex_jsonl_root": str(FIXTURE_ROOT / "codex"),
            "claude_code_jsonl_root": str(FIXTURE_ROOT / "claude_code"),
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z",
        },
    )

    assert exit_code == 0
    assert stderr == ""
    assert "error" not in payload
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert str(database_path) not in text
    assert "experiments/fixtures" not in text
    assert database_path.exists()

    connection = connect_database(database_path)
    try:
        summary = query_daily_summary(connection, "2026-06-14")
    finally:
        connection.close()
    assert summary.totals.total_tokens == 7570


def test_sidecar_load_storage_summary_reads_database_path_from_env(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "usage.sqlite"
    monkeypatch.setenv(REFRESH_DATABASE_PATH_ENV_VAR, str(database_path))
    run_sidecar_payload(
        PRIMARY_REFRESH_COMMAND_NAME,
        {
            "codex_jsonl_root": str(FIXTURE_ROOT / "codex"),
            "end_day_utc": "2026-06-14",
        },
    )

    exit_code, text, stderr, payload = run_sidecar_payload(
        LOAD_STORAGE_SUMMARY_COMMAND_NAME,
        {"end_day_utc": "2026-06-14"},
    )

    assert exit_code == 0
    assert stderr == ""
    assert payload["summary"]["totals"]["total_tokens"] == 2540
    assert str(database_path) not in text


def test_sidecar_manual_allowance_uses_database_path_from_env(tmp_path, monkeypatch):
    database_path = tmp_path / "usage.sqlite"
    monkeypatch.setenv(REFRESH_DATABASE_PATH_ENV_VAR, str(database_path))

    exit_code, text, stderr, payload = run_sidecar_payload(
        SAVE_MANUAL_ALLOWANCE_COMMAND_NAME,
        {
            "end_day_utc": "2026-06-14",
            "source_kind": "claude_code",
            "unit": "tokens",
            "limit_amount": 200000,
            "reset_at": "2026-06-21T00:00:00Z",
        },
    )

    assert exit_code == 0
    assert stderr == ""
    assert "error" not in payload
    assert str(database_path) not in text

    connection = connect_database(database_path)
    try:
        windows = query_allowance_windows(connection)
    finally:
        connection.close()
    assert len(windows) == 1
    assert windows[0].source_kind == "claude_code"


def test_sidecar_billing_sync_reports_missing_env_without_echoing_key_name(monkeypatch):
    monkeypatch.delenv(OPENAI_ADMIN_KEY_ENV_VAR, raising=False)

    exit_code, text, stderr, payload = run_sidecar_payload(
        SYNC_API_PROVIDER_BILLING_COMMAND_NAME,
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
        },
    )

    assert exit_code == 0
    assert stderr == ""
    assert payload == {
        "error": {
            "code": "api_provider_billing_sync_unavailable",
            "field": "credential",
            "message": "OpenAI API provider credential is not configured",
        }
    }
    assert OPENAI_ADMIN_KEY_ENV_VAR not in text


def test_sidecar_non_billing_commands_clear_inherited_openai_key(monkeypatch):
    monkeypatch.setenv(OPENAI_ADMIN_KEY_ENV_VAR, "sk-admin-inherited-secret")

    exit_code, text, stderr, payload = run_sidecar_payload(
        PRIMARY_REFRESH_COMMAND_NAME,
        {"end_day_utc": "2026-6-14"},
    )

    assert exit_code == 0
    assert stderr == ""
    assert payload["error"]["code"] == "invalid_refresh_request"
    assert OPENAI_ADMIN_KEY_ENV_VAR not in text
    assert "sk-admin-inherited-secret" not in text
    assert OPENAI_ADMIN_KEY_ENV_VAR not in os.environ


def test_sidecar_unknown_command_returns_fixed_launcher_error_without_reading_stdin():
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run_sidecar_command_io(
        ["yth-backend", "C:/Users/example/secret/backend"],
        io.StringIO('{"source_root": "C:/Users/example/secret/codex"}'),
        stdout,
        stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "unknown backend command\n"
    assert "C:/Users" not in stderr.getvalue()
    assert "secret" not in stderr.getvalue()


def test_sidecar_missing_command_returns_fixed_launcher_error():
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run_sidecar_command_io(
        ["yth-backend"],
        io.StringIO("{}"),
        stdout,
        stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "backend command is required\n"
