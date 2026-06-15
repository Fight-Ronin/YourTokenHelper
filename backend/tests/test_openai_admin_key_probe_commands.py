import json
from pathlib import Path

from backend.sources import (
    OPENAI_ADMIN_KEY_ENV_VAR,
    OPENAI_ADMIN_KEY_PROBE_COMMAND_NAME,
    build_openai_admin_key_probe_command_response_from_json,
    build_openai_admin_key_probe_command_response_from_mapping,
    build_openai_admin_key_probe_command_response_json,
    openai_admin_key_probe_command_request_from_mapping,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_admin_api_keys_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_openai_admin_key_probe_command_request_accepts_checked_at_only():
    request = openai_admin_key_probe_command_request_from_mapping(
        {"checked_at": "2026-06-15T08:00:00+08:00"}
    )

    assert OPENAI_ADMIN_KEY_PROBE_COMMAND_NAME == "probe_openai_admin_api_key"
    assert request.checked_at == "2026-06-15T00:00:00Z"


def test_openai_admin_key_probe_command_requires_admin_env_not_personal_env():
    payload = build_openai_admin_key_probe_command_response_from_mapping(
        {"checked_at": "2026-06-15T00:00:00Z"},
        env={"OPENAI_API_KEY": "sk-personal-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "openai_admin_key_probe_unavailable",
            "field": "environment",
            "message": "OpenAI Admin API key is not configured",
        }
    }
    assert "sk-personal-fixture-secret" not in text


def test_openai_admin_key_probe_command_rejects_key_material_fields():
    payload = build_openai_admin_key_probe_command_response_from_mapping(
        {
            "api_key": "sk-admin-fixture-secret",
            "checked_at": "2026-06-15T00:00:00Z",
            "payload": fixture_payload(),
        },
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_openai_admin_key_probe_request"
    assert "unsupported OpenAI Admin key probe fields" in payload["error"]["message"]
    assert "api_key" in payload["error"]["message"]
    assert "payload" in payload["error"]["message"]
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture_admin" not in text


def test_openai_admin_key_probe_command_maps_permission_denied_without_body_echo():
    payload = build_openai_admin_key_probe_command_response_from_mapping(
        {"checked_at": "2026-06-15T00:00:00Z"},
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-personal-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: {
            "admin_api_keys": {
                "error": {
                    "status": 403,
                    "body": {"error": {"message": "fixture secret detail"}},
                }
            }
        },
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["monitor_result"]["status"] == "permission_denied"
    assert payload["monitor_result"]["confidence"] == "unavailable"
    assert payload["monitor_result"]["message"] == (
        "OpenAI Admin API key listing access was denied."
    )
    assert "fixture secret detail" not in text
    assert "sk-personal-fixture-secret" not in text


def test_openai_admin_key_probe_command_returns_redacted_success():
    seen = {}

    def fake_fetch(api_key):
        seen["api_key"] = api_key
        return fixture_payload()

    payload = build_openai_admin_key_probe_command_response_from_mapping(
        {"checked_at": "2026-06-15T00:00:00Z"},
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_admin_api_keys=fake_fetch,
    )
    text = json.dumps(payload, sort_keys=True)

    assert seen == {"api_key": "sk-admin-fixture-secret"}
    assert payload["monitor_result"]["status"] == "ready"
    assert payload["monitor_result"]["key_count"] == 2
    assert payload["monitor_result"]["keys"][0]["api_key_id"].startswith("api-key_")
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture_admin" not in text
    assert "sk-admin" not in text
    assert "Main Admin Key" not in text


def test_openai_admin_key_probe_command_unsupported_endpoint_is_unavailable():
    payload = build_openai_admin_key_probe_command_response_from_mapping(
        {"checked_at": "2026-06-15T00:00:00Z"},
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: {"admin_api_keys": {}},
    )

    assert payload == {
        "error": {
            "code": "openai_admin_key_probe_unavailable",
            "field": "endpoint",
            "message": "OpenAI Admin API key probe returned an unsupported response",
        }
    }


def test_openai_admin_key_probe_command_response_from_json_rejects_non_json_without_echo():
    payload = build_openai_admin_key_probe_command_response_from_json(
        '{"api_key":"sk-admin-fixture-secret",'
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_key_probe_request",
            "message": "OpenAI Admin key probe request must be valid JSON",
        }
    }
    assert "sk-admin-fixture-secret" not in text


def test_openai_admin_key_probe_command_response_json_serializes_newline():
    text = build_openai_admin_key_probe_command_response_json(
        json.dumps({"checked_at": "2026-06-15T00:00:00Z"}),
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )
    payload = json.loads(text)

    assert text.endswith("\n")
    assert payload["monitor_result"]["status"] == "ready"
    assert "key_fixture_admin" not in text
