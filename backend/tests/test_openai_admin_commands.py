import json
import sqlite3
from pathlib import Path

from backend.sources import (
    OPENAI_ADMIN_SYNC_COMMAND_NAME,
    OpenAIAdminSyncCommandError,
    build_openai_admin_sync_command_payload,
    build_openai_admin_sync_command_payload_from_request,
    build_openai_admin_sync_command_response_from_json,
    build_openai_admin_sync_command_response_from_mapping,
    build_openai_admin_sync_command_response_json,
    openai_admin_sync_command_error_to_payload,
    openai_admin_sync_command_request_from_mapping,
)
from backend.storage import (
    initialize_schema,
    query_cost_total_usd,
    query_rolling_7d_summary,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_probe_response.json")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_openai_admin_sync_command_request_parses_payload_boundary():
    request = openai_admin_sync_command_request_from_mapping(
        {
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T08:00:00+08:00",
            "payload": fixture_payload(),
        }
    )

    assert OPENAI_ADMIN_SYNC_COMMAND_NAME == "sync_openai_admin_usage_cost"
    assert request.end_day_utc == "2026-06-13"
    assert request.started_at == "2026-06-14T00:00:00Z"
    assert request.payload["usage"]["data"]


def test_openai_admin_sync_command_payload_from_request_syncs_existing_contract():
    connection = memory_connection()
    request = openai_admin_sync_command_request_from_mapping(
        {
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T00:00:00Z",
            "payload": fixture_payload(),
        }
    )

    payload = build_openai_admin_sync_command_payload_from_request(
        request,
        connection=connection,
    )

    assert payload["sync_result"]["usage_events_seen"] == 3
    assert payload["sync_result"]["cost_records_seen"] == 2
    assert payload["sync_result"]["events_seen"] == 5
    assert payload["storage_summary"]["summary"]["event_count"] == 109
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 43100
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") == 1.03


def test_openai_admin_sync_command_response_from_mapping_returns_redacted_success():
    connection = memory_connection()

    payload = build_openai_admin_sync_command_response_from_mapping(
        {
            "end_day_utc": "2026-06-13",
            "started_at": "2026-06-14T00:00:00Z",
            "payload": fixture_payload(),
        },
        connection=connection,
    )
    text = json.dumps(payload, sort_keys=True)

    assert "error" not in payload
    assert payload["sync_result"]["source_kind"] == "openai_api_cost"
    assert payload["sync_result"]["status"] == "ready"
    assert payload["storage_summary"]["generated_from"] == (
        "backend.sources.openai_admin_commands"
    )
    assert "key_fixture" not in text
    assert "proj_fixture" not in text
    assert str(FIXTURE_PATH) not in text


def test_openai_admin_sync_command_response_from_json_serializes_success_with_newline():
    text = build_openai_admin_sync_command_response_json(
        json.dumps(
            {
                "end_day_utc": "2026-06-13",
                "started_at": "2026-06-14T00:00:00Z",
                "payload": fixture_payload(),
            }
        ),
        connection=memory_connection(),
    )
    payload = json.loads(text)

    assert text.endswith("\n")
    assert "error" not in payload
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 43100
    assert "key_fixture" not in text
    assert "proj_fixture" not in text


def test_openai_admin_sync_command_rejects_database_path_request_field_without_echo():
    payload = build_openai_admin_sync_command_response_from_mapping(
        {
            "database_path": "C:/Users/example/secret/usage.sqlite",
            "end_day_utc": "2026-06-13",
            "payload": fixture_payload(),
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_openai_admin_sync_request"
    assert "unsupported OpenAI Admin sync fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert "C:/Users" not in text
    assert "secret" not in text
    assert "key_fixture" not in text


def test_openai_admin_sync_command_rejects_invalid_end_day_without_payload_echo():
    payload = build_openai_admin_sync_command_response_from_mapping(
        {
            "end_day_utc": "2026-6-13",
            "payload": fixture_payload(),
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
    assert "key_fixture" not in text
    assert "proj_fixture" not in text


def test_openai_admin_sync_command_rejects_invalid_started_at():
    payload = build_openai_admin_sync_command_response_from_mapping(
        {
            "end_day_utc": "2026-06-13",
            "started_at": "not-a-timestamp",
            "payload": fixture_payload(),
        }
    )

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "field": "started_at",
            "message": "started_at must be ISO-8601",
        }
    }


def test_openai_admin_sync_command_rejects_non_object_payload():
    payload = build_openai_admin_sync_command_response_from_mapping(
        {
            "end_day_utc": "2026-06-13",
            "payload": [],
        }
    )

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "field": "payload",
            "message": "payload must be a JSON object",
        }
    }


def test_openai_admin_sync_command_response_from_json_rejects_non_json_stdin():
    payload = build_openai_admin_sync_command_response_from_json(
        '{"payload":{"api_key_id":"key_fixture_hidden"},'
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "message": "OpenAI Admin sync request must be valid JSON",
        }
    }
    assert "key_fixture_hidden" not in text


def test_openai_admin_sync_command_response_from_json_rejects_non_object_stdin():
    payload = build_openai_admin_sync_command_response_from_json(json.dumps(["not-object"]))

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "message": "OpenAI Admin sync request must be a JSON object",
        }
    }


def test_openai_admin_sync_command_error_payload_is_structured():
    try:
        openai_admin_sync_command_request_from_mapping(
            {
                "end_day_utc": "2026-6-13",
                "payload": fixture_payload(),
            }
        )
    except OpenAIAdminSyncCommandError as exc:
        payload = openai_admin_sync_command_error_to_payload(exc)
    else:
        raise AssertionError("expected invalid end_day_utc")

    assert payload == {
        "error": {
            "code": "invalid_openai_admin_sync_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }


def test_openai_admin_sync_command_keeps_usage_when_costs_are_permission_denied():
    connection = memory_connection()
    admin_payload = fixture_payload()
    admin_payload["costs"] = {
        "error": {"status": 403, "body": {"error": {"code": "missing_scope"}}}
    }

    payload = build_openai_admin_sync_command_payload(
        connection=connection,
        payload=admin_payload,
        end_day_utc="2026-06-13",
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_rolling_7d_summary(connection, "2026-06-13")

    assert payload["sync_result"]["status"] == "ready"
    assert payload["sync_result"]["usage_events_seen"] == 3
    assert payload["sync_result"]["cost_records_seen"] == 0
    assert summary.event_count == 109
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") is None
