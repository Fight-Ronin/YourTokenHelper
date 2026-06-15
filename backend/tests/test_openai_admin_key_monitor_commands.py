import json
from pathlib import Path

from backend.sources import (
    OPENAI_ADMIN_KEY_MONITOR_COMMAND_NAME,
    build_openai_admin_key_monitor_command_response_from_json,
    build_openai_admin_key_monitor_command_response_from_mapping,
    build_openai_admin_key_monitor_command_response_json,
    openai_admin_key_monitor_command_request_from_mapping,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_admin_api_keys_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_openai_admin_key_monitor_command_request_parses_payload_boundary():
    request = openai_admin_key_monitor_command_request_from_mapping(
        {
            "checked_at": "2026-06-15T08:00:00+08:00",
            "payload": fixture_payload(),
        }
    )

    assert OPENAI_ADMIN_KEY_MONITOR_COMMAND_NAME == "monitor_openai_admin_api_key"
    assert request.checked_at == "2026-06-15T00:00:00Z"
    assert request.payload["admin_api_keys"]["data"]


def test_openai_admin_key_monitor_command_returns_redacted_success():
    payload = build_openai_admin_key_monitor_command_response_from_mapping(
        {
            "checked_at": "2026-06-15T00:00:00Z",
            "payload": fixture_payload(),
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["monitor_result"]["status"] == "ready"
    assert payload["monitor_result"]["key_count"] == 2
    assert payload["monitor_result"]["active_key_count"] == 1
    assert "key_fixture_admin" not in text
    assert "sk-admin" not in text
    assert "Main Admin Key" not in text
    assert "Usage Monitor Service Account" not in text


def test_openai_admin_key_monitor_command_rejects_key_material_fields():
    payload = build_openai_admin_key_monitor_command_response_from_mapping(
        {
            "api_key": "sk-admin-fixture-secret",
            "database_path": "C:/Users/example/secret/usage.sqlite",
            "checked_at": "2026-06-15T00:00:00Z",
            "payload": fixture_payload(),
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_openai_admin_key_monitor_request"
    assert "unsupported OpenAI Admin key monitor fields" in payload["error"]["message"]
    assert "api_key" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert "sk-admin-fixture-secret" not in text
    assert "C:/Users" not in text
    assert "secret" not in text


def test_openai_admin_key_monitor_command_rejects_invalid_checked_at_without_payload_echo():
    payload = build_openai_admin_key_monitor_command_response_from_mapping(
        {
            "checked_at": "not-a-timestamp",
            "payload": fixture_payload(),
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_key_monitor_request",
            "field": "checked_at",
            "message": "checked_at must be ISO-8601",
        }
    }
    assert "key_fixture_admin" not in text


def test_openai_admin_key_monitor_command_rejects_missing_endpoint():
    payload = build_openai_admin_key_monitor_command_response_from_mapping(
        {
            "checked_at": "2026-06-15T00:00:00Z",
            "payload": {},
        }
    )

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_key_monitor_request",
            "field": "payload",
            "message": "OpenAI Admin API keys endpoint payload is required",
        }
    }


def test_openai_admin_key_monitor_command_response_from_json_rejects_non_json_without_echo():
    payload = build_openai_admin_key_monitor_command_response_from_json(
        '{"payload":{"admin_api_keys":{"data":[{"id":"key_fixture_admin_hidden"}]}},'
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_key_monitor_request",
            "message": "OpenAI Admin key monitor request must be valid JSON",
        }
    }
    assert "key_fixture_admin_hidden" not in text


def test_openai_admin_key_monitor_command_response_json_serializes_newline():
    text = build_openai_admin_key_monitor_command_response_json(
        json.dumps(
            {
                "checked_at": "2026-06-15T00:00:00Z",
                "payload": fixture_payload(),
            }
        )
    )
    payload = json.loads(text)

    assert text.endswith("\n")
    assert payload["monitor_result"]["status"] == "ready"
    assert "key_fixture_admin" not in text
