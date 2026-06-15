import json
import sqlite3
from pathlib import Path

from backend.sources import OPENAI_ADMIN_KEY_ENV_VAR
from backend.sources.api_provider_billing_sync_commands import (
    SYNC_API_PROVIDER_BILLING_COMMAND_NAME,
    api_provider_billing_sync_command_error_to_payload,
    api_provider_billing_sync_command_request_from_mapping,
    build_api_provider_billing_sync_command_response_from_mapping,
)
from backend.storage import initialize_schema, query_cost_total_usd, query_rolling_7d_summary


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_probe_response.json")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_api_provider_billing_sync_command_request_parses_minimal_boundary():
    request = api_provider_billing_sync_command_request_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T08:00:00+08:00",
        }
    )

    assert SYNC_API_PROVIDER_BILLING_COMMAND_NAME == "sync_api_provider_billing"
    assert request.provider_id == "openai_api_cost"
    assert request.end_day_utc == "2026-06-13"
    assert request.started_at == "2026-06-14T00:00:00Z"


def test_api_provider_billing_sync_command_rejects_key_material_fields_without_echo():
    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
            "api_key": "sk-admin-fixture-secret",
            "database_path": "C:/Users/example/secret/usage.sqlite",
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_api_provider_billing_sync_request"
    assert "unsupported API provider billing sync fields" in payload["error"]["message"]
    assert "api_key" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert "sk-admin-fixture-secret" not in text
    assert "C:/Users" not in text
    assert "secret" not in text


def test_api_provider_billing_sync_command_rejects_unknown_provider_without_echo():
    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "C:/Users/example/secret/provider",
            "end_day_utc": "2026-06-13",
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_api_provider_billing_sync_request",
            "field": "provider_id",
            "message": "Unknown API cost provider",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_api_provider_billing_sync_command_rejects_unverified_provider_explicitly():
    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "claude_api_cost",
            "end_day_utc": "2026-06-13",
        },
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
    )

    assert payload == {
        "error": {
            "code": "api_provider_billing_sync_unavailable",
            "field": "provider_id",
            "message": "Provider billing adapter has not been verified",
        }
    }


def test_api_provider_billing_sync_command_requires_configured_openai_credential():
    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
        },
        env={},
    )

    assert payload == {
        "error": {
            "code": "api_provider_billing_sync_unavailable",
            "field": "credential",
            "message": "OpenAI API provider credential is not configured",
        }
    }


def test_api_provider_billing_sync_command_syncs_openai_payload_to_storage():
    connection = memory_connection()
    seen_keys: list[str] = []

    def fake_fetch(api_key: str, *, end_day_utc: str):
        seen_keys.append(api_key)
        assert end_day_utc == "2026-06-13"
        return fixture_payload()

    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T00:00:00Z",
        },
        connection=connection,
        env={OPENAI_ADMIN_KEY_ENV_VAR: " sk-admin-fixture-secret "},
        fetch_provider_billing=fake_fetch,
    )
    text = json.dumps(payload, sort_keys=True)

    assert seen_keys == ["sk-admin-fixture-secret"]
    assert "error" not in payload
    assert payload["provider_status"]["provider_id"] == "openai_api_cost"
    assert payload["provider_status"]["status"] == "ready"
    assert payload["provider_status"]["credential_configured"] is True
    assert payload["endpoint_statuses"] == {
        "usage": "ready",
        "costs": "ready",
    }
    assert payload["sync_result"]["usage_events_seen"] == 3
    assert payload["sync_result"]["cost_records_seen"] == 2
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 43100
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") == 1.03
    assert "sk-admin-fixture-secret" not in text
    assert "key_fixture" not in text
    assert "proj_fixture" not in text


def test_api_provider_billing_sync_command_maps_permission_denied_without_replacing_storage():
    connection = memory_connection()
    build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
        },
        connection=connection,
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_provider_billing=lambda *_args, **_kwargs: fixture_payload(),
    )

    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T01:00:00Z",
        },
        connection=connection,
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-personal-fixture-secret"},
        fetch_provider_billing=lambda *_args, **_kwargs: {
            "usage": {"error": {"status": 403, "body": "must not leak"}},
            "costs": {"error": {"status": 403, "body": "must not leak"}},
        },
    )
    text = json.dumps(payload, sort_keys=True)
    summary = query_rolling_7d_summary(connection, "2026-06-13")

    assert "error" not in payload
    assert payload["sync_result"]["status"] == "permission_denied"
    assert payload["provider_status"]["status"] == "permission_denied"
    assert payload["endpoint_statuses"] == {
        "usage": "permission_denied",
        "costs": "permission_denied",
    }
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") == 1.03
    assert summary.by_source["openai_api_cost"].total_tokens == 43100
    assert "sk-personal-fixture-secret" not in text
    assert "must not leak" not in text


def test_api_provider_billing_sync_command_reports_mixed_endpoint_diagnostics():
    connection = memory_connection()
    admin_payload = fixture_payload()
    admin_payload["costs"] = {"error": {"status": 429, "body": "must not leak"}}

    payload = build_api_provider_billing_sync_command_response_from_mapping(
        {
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-13",
        },
        connection=connection,
        env={OPENAI_ADMIN_KEY_ENV_VAR: "sk-admin-fixture-secret"},
        fetch_provider_billing=lambda *_args, **_kwargs: admin_payload,
    )
    text = json.dumps(payload, sort_keys=True)

    assert "error" not in payload
    assert payload["provider_status"]["status"] == "rate_limited"
    assert payload["endpoint_statuses"] == {
        "usage": "ready",
        "costs": "rate_limited",
    }
    assert "sk-admin-fixture-secret" not in text
    assert "must not leak" not in text


def test_api_provider_billing_sync_command_error_payload_is_structured():
    try:
        api_provider_billing_sync_command_request_from_mapping(
            {
                "provider_id": "openai_api_cost",
                "end_day_utc": "2026-6-13",
            }
        )
    except Exception as exc:
        payload = api_provider_billing_sync_command_error_to_payload(exc)
    else:
        raise AssertionError("expected invalid end_day_utc")

    assert payload == {
        "error": {
            "code": "invalid_api_provider_billing_sync_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
