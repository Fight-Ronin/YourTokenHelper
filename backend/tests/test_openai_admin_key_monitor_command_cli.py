import io
import json
from pathlib import Path

from backend.sources.openai_admin_key_monitor_command_cli import (
    run_openai_admin_key_monitor_command_io,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_admin_api_keys_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def run_cli_payload(payload: object):
    stdout = io.StringIO()
    exit_code = run_openai_admin_key_monitor_command_io(
        io.StringIO(json.dumps(payload)),
        stdout,
    )
    return exit_code, stdout.getvalue(), json.loads(stdout.getvalue())


def test_openai_admin_key_monitor_command_cli_returns_redacted_success():
    exit_code, text, payload = run_cli_payload(
        {
            "checked_at": "2026-06-15T00:00:00Z",
            "payload": fixture_payload(),
        }
    )

    assert exit_code == 0
    assert text.endswith("\n")
    assert payload["monitor_result"]["status"] == "ready"
    assert payload["monitor_result"]["key_count"] == 2
    assert "key_fixture_admin" not in text
    assert "sk-admin" not in text
    assert "Main Admin Key" not in text
    assert "Usage Monitor Service Account" not in text


def test_openai_admin_key_monitor_command_cli_rejects_key_material_fields():
    exit_code, text, payload = run_cli_payload(
        {
            "api_key": "sk-admin-fixture-secret",
            "checked_at": "2026-06-15T00:00:00Z",
            "payload": fixture_payload(),
        }
    )

    assert exit_code == 0
    assert payload["error"]["code"] == "invalid_openai_admin_key_monitor_request"
    assert "api_key" in payload["error"]["message"]
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture_admin" not in text


def test_openai_admin_key_monitor_command_cli_rejects_non_json_stdin():
    stdout = io.StringIO()
    exit_code = run_openai_admin_key_monitor_command_io(io.StringIO("not-json"), stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload == {
        "error": {
            "code": "invalid_openai_admin_key_monitor_request",
            "message": "OpenAI Admin key monitor request must be valid JSON",
        }
    }
