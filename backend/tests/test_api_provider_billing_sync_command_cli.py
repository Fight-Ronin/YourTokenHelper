import io
import json
from pathlib import Path

from backend.sources import OPENAI_ADMIN_KEY_ENV_VAR
from backend.sources.api_provider_billing_sync_command_cli import (
    run_api_provider_billing_sync_command_io,
)
from backend.storage import connect_database, query_cost_total_usd, query_rolling_7d_summary


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_probe_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def run_cli_payload(
    payload: object,
    *,
    database_path: str | Path | None = None,
    fetch_provider_billing=None,
):
    stdout = io.StringIO()
    exit_code = run_api_provider_billing_sync_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
        database_path=database_path,
        fetch_provider_billing=fetch_provider_billing,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def test_api_provider_billing_sync_command_cli_can_use_file_backed_database(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(OPENAI_ADMIN_KEY_ENV_VAR, "sk-admin-fixture-secret")
    database_path = tmp_path / "usage.sqlite"

    exit_code, text, payload = run_cli_payload(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T00:00:00Z",
        },
        database_path=database_path,
        fetch_provider_billing=lambda *_args, **_kwargs: fixture_payload(),
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert "error" not in payload
    assert payload["provider_status"]["status"] == "ready"
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 43100
    assert str(database_path) not in text
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture" not in text

    connection = connect_database(database_path)
    try:
        summary = query_rolling_7d_summary(connection, "2026-06-13")
        cost_total = query_cost_total_usd(connection, "2026-06-12", "2026-06-13")
    finally:
        connection.close()
    assert summary.totals.total_tokens == 43100
    assert cost_total == 1.03


def test_api_provider_billing_sync_command_cli_reports_missing_env_without_live_fetch(
    monkeypatch,
):
    monkeypatch.delenv(OPENAI_ADMIN_KEY_ENV_VAR, raising=False)

    exit_code, text, payload = run_cli_payload(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
        },
        fetch_provider_billing=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("fetch should not run without a key")
        ),
    )

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "api_provider_billing_sync_unavailable",
            "field": "credential",
            "message": "OpenAI API provider credential is not configured",
        }
    }
    assert "OPENAI_ADMIN_KEY" not in text


def test_api_provider_billing_sync_command_cli_rejects_non_json_stdin():
    stdout = io.StringIO()
    exit_code = run_api_provider_billing_sync_command_io(io.StringIO("not-json"), stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_api_provider_billing_sync_request",
            "message": "API provider billing sync request must be valid JSON",
        }
    }
