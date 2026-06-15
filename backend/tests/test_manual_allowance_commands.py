import json
import sqlite3

from backend.sources import (
    SAVE_MANUAL_ALLOWANCE_COMMAND_NAME,
    ManualAllowanceCommandError,
    build_manual_allowance_command_payload_from_request,
    build_manual_allowance_command_response_from_json,
    build_manual_allowance_command_response_from_mapping,
    build_manual_allowance_command_response_json,
    manual_allowance_command_error_to_payload,
    manual_allowance_command_request_from_mapping,
)
from backend.storage import initialize_schema, query_allowance_windows


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def manual_request(**overrides):
    request = {
        "end_day_utc": "2026-06-14",
        "source_kind": "codex",
        "unit": "tokens",
        "limit_amount": 100000,
        "reset_at": "2026-06-21T08:00:00+08:00",
    }
    request.update(overrides)
    return request


def test_manual_allowance_command_request_parses_redacted_manual_window():
    request = manual_allowance_command_request_from_mapping(
        manual_request(
            window_start="2026-06-14T08:00:00+08:00",
            window_end="2026-06-21T08:00:00+08:00",
            used_amount=2540,
            remaining_amount=97460,
        )
    )

    assert SAVE_MANUAL_ALLOWANCE_COMMAND_NAME == "save_manual_allowance_window"
    assert request.end_day_utc == "2026-06-14"
    assert request.allowance_window.source_kind == "codex"
    assert request.allowance_window.source_id == "codex:manual_allowance"
    assert request.allowance_window.status == "manual"
    assert request.allowance_window.window_start == "2026-06-14T00:00:00Z"
    assert request.allowance_window.window_end == "2026-06-21T00:00:00Z"
    assert request.allowance_window.reset_at == "2026-06-21T00:00:00Z"
    assert request.allowance_window.limit_amount == 100000
    assert request.allowance_window.used_amount == 2540
    assert request.allowance_window.remaining_amount == 97460
    assert request.allowance_window.note is None


def test_manual_allowance_command_payload_persists_window_in_storage_summary():
    connection = memory_connection()
    request = manual_allowance_command_request_from_mapping(manual_request())

    payload = build_manual_allowance_command_payload_from_request(
        request,
        connection=connection,
    )
    windows = query_allowance_windows(connection)
    text = json.dumps(payload, sort_keys=True)

    assert "error" not in payload
    assert payload["allowance_window"] == {
        "source_kind": "codex",
        "source_id": "codex:manual_allowance",
        "status": "manual",
        "unit": "tokens",
        "reset_at": "2026-06-21T00:00:00Z",
        "limit_amount": 100000,
    }
    assert payload["storage_summary"]["generated_from"] == (
        "backend.sources.manual_allowance_commands"
    )
    assert payload["storage_summary"]["allowance_windows"] == [payload["allowance_window"]]
    assert len(windows) == 1
    assert windows[0].source_id == "codex:manual_allowance"
    assert "C:/Users" not in text
    assert "secret" not in text


def test_manual_allowance_command_response_from_mapping_replaces_same_source_kind():
    connection = memory_connection()

    first = build_manual_allowance_command_response_from_mapping(
        manual_request(limit_amount=100000),
        connection=connection,
    )
    second = build_manual_allowance_command_response_from_mapping(
        manual_request(limit_amount=200000, remaining_amount=150000),
        connection=connection,
    )
    windows = query_allowance_windows(connection)

    assert "error" not in first
    assert "error" not in second
    assert len(windows) == 1
    assert windows[0].source_id == "codex:manual_allowance"
    assert windows[0].limit_amount == 200000
    assert windows[0].remaining_amount == 150000


def test_manual_allowance_command_response_from_json_serializes_success_with_newline():
    text = build_manual_allowance_command_response_json(
        json.dumps(manual_request()),
        connection=memory_connection(),
    )
    payload = json.loads(text)

    assert text.endswith("\n")
    assert "error" not in payload
    assert payload["allowance_window"]["status"] == "manual"
    assert payload["storage_summary"]["allowance_windows"][0]["limit_amount"] == 100000


def test_manual_allowance_command_rejects_user_controlled_identity_fields():
    payload = build_manual_allowance_command_response_from_mapping(
        manual_request(
            source_id="codex:C:/Users/example/secret",
            note="C:/Users/example/secret",
        )
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_manual_allowance_request"
    assert "unsupported manual allowance fields" in payload["error"]["message"]
    assert "source_id" in payload["error"]["message"]
    assert "note" in payload["error"]["message"]
    assert "C:/Users" not in text
    assert "secret" not in text


def test_manual_allowance_command_rejects_database_path_request_field_without_echo():
    payload = build_manual_allowance_command_response_from_mapping(
        manual_request(database_path="C:/Users/example/secret/usage.sqlite")
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_manual_allowance_request"
    assert "unsupported manual allowance fields" in payload["error"]["message"]
    assert "database_path" in payload["error"]["message"]
    assert "C:/Users" not in text
    assert "secret" not in text


def test_manual_allowance_command_rejects_unknown_source_values_without_echo():
    payload = build_manual_allowance_command_response_from_mapping(
        manual_request(source_kind="C:/Users/example/secret/codex")
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "source_kind",
            "message": "unknown source_kind",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text

    payload = build_manual_allowance_command_response_from_mapping(
        manual_request(unit="C:/Users/example/secret/unit")
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "unit",
            "message": "unknown allowance unit",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_manual_allowance_command_sanitizes_unsupported_field_names():
    payload = build_manual_allowance_command_response_from_mapping(
        {
            **manual_request(),
            "C:/Users/example/secret": True,
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload["error"]["code"] == "invalid_manual_allowance_request"
    assert "<unsupported>" in payload["error"]["message"]
    assert "C:/Users" not in text
    assert "secret" not in text


def test_manual_allowance_command_rejects_invalid_limit_amount():
    assert build_manual_allowance_command_response_from_mapping(
        manual_request(limit_amount=0)
    ) == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "limit_amount",
            "message": "limit_amount must be positive",
        }
    }
    assert build_manual_allowance_command_response_from_mapping(
        manual_request(limit_amount=True)
    ) == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "limit_amount",
            "message": "limit_amount must be a number",
        }
    }


def test_manual_allowance_command_rejects_invalid_timestamps():
    assert build_manual_allowance_command_response_from_mapping(
        manual_request(window_start="2026-06-21T00:00:00Z", window_end="2026-06-14T00:00:00Z")
    ) == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "window_end",
            "message": "window_end must be after window_start",
        }
    }
    assert build_manual_allowance_command_response_from_mapping(
        manual_request(reset_at="not-a-timestamp")
    ) == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "reset_at",
            "message": "reset_at must be ISO-8601",
        }
    }


def test_manual_allowance_command_response_from_json_rejects_invalid_json_without_echo():
    payload = build_manual_allowance_command_response_from_json(
        '{"note":"C:/Users/example/secret",'
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "message": "manual allowance request must be valid JSON",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_manual_allowance_command_error_payload_is_structured():
    try:
        manual_allowance_command_request_from_mapping(manual_request(end_day_utc="2026-6-14"))
    except ManualAllowanceCommandError as exc:
        payload = manual_allowance_command_error_to_payload(exc)
    else:
        raise AssertionError("expected invalid end_day_utc")

    assert payload == {
        "error": {
            "code": "invalid_manual_allowance_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
