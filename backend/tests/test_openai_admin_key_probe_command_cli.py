import io
import json
from pathlib import Path

from backend.sources import OPENAI_ADMIN_KEY_ENV_VAR
from backend.sources.openai_admin_key_probe_command_cli import (
    run_openai_admin_key_probe_command_io,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_admin_api_keys_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def run_cli_payload(
    payload: object,
    *,
    env: dict[str, str] | None = None,
    fetch_admin_api_keys=None,
):
    stdout = io.StringIO()
    exit_code = run_openai_admin_key_probe_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
        env=env,
        fetch_admin_api_keys=fetch_admin_api_keys,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def test_openai_admin_key_probe_command_cli_returns_redacted_success():
    exit_code, text, payload = run_cli_payload(
        {"checked_at": "2026-06-15T00:00:00Z"},
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert payload["monitor_result"]["status"] == "ready"
    assert payload["monitor_result"]["key_count"] == 2
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture_admin" not in text
    assert "Main Admin Key" not in text


def test_openai_admin_key_probe_command_cli_rejects_key_material_fields():
    exit_code, text, payload = run_cli_payload(
        {
            "api_key": "sk-admin-fixture-secret",
            "checked_at": "2026-06-15T00:00:00Z",
        },
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_openai_admin_key_probe_request"
    assert "api_key" in payload["error"]["message"]
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture_admin" not in text


def test_openai_admin_key_probe_command_cli_rejects_non_json_stdin():
    stdout = io.StringIO()
    exit_code = run_openai_admin_key_probe_command_io(io.StringIO("not-json"), stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_openai_admin_key_probe_request",
            "message": "OpenAI Admin key probe request must be valid JSON",
        }
    }


def test_openai_admin_key_probe_command_cli_reports_missing_env_without_live_fetch():
    exit_code, text, payload = run_cli_payload(
        {"checked_at": "2026-06-15T00:00:00Z"},
        env={},
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "openai_admin_key_probe_unavailable"
    assert payload["error"]["field"] == "environment"
    assert "key_fixture_admin" not in text
