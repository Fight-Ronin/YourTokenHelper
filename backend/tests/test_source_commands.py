import json
import sqlite3
from pathlib import Path

from backend.sources import (
    PRIMARY_REFRESH_COMMAND_NAME,
    PrimaryRefreshCommandError,
    build_primary_refresh_command_payload,
    build_primary_refresh_command_payload_from_request,
    build_primary_refresh_command_response_from_json,
    build_primary_refresh_command_response_from_mapping,
    build_primary_refresh_command_response_json,
    primary_jsonl_candidates,
    primary_refresh_command_error_to_payload,
    primary_refresh_command_request_from_mapping,
)
from backend.storage import initialize_schema, query_daily_summary


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_primary_jsonl_candidates_include_only_explicit_roots():
    candidates = primary_jsonl_candidates(codex_jsonl_root=FIXTURE_ROOT / "codex")

    assert len(candidates) == 1
    assert candidates[0].source_kind == "codex"
    assert candidates[0].root == FIXTURE_ROOT / "codex"


def test_primary_refresh_command_request_parses_explicit_roots():
    request = primary_refresh_command_request_from_mapping(
        {
            "codex_jsonl_root": "experiments/fixtures/local_sources/codex",
            "claude_code_jsonl_root": "experiments/fixtures/local_sources/claude_code",
            "cursor_jsonl_root": "experiments/fixtures/local_sources/cursor",
            "gemini_cli_jsonl_root": "experiments/fixtures/local_sources/gemini_cli",
            "github_copilot_jsonl_root": "experiments/fixtures/local_sources/github_copilot",
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T08:00:00+08:00",
        }
    )

    assert PRIMARY_REFRESH_COMMAND_NAME == "refresh_sources_manual"
    assert request.codex_jsonl_root == FIXTURE_ROOT / "codex"
    assert request.claude_code_jsonl_root == FIXTURE_ROOT / "claude_code"
    assert request.cursor_jsonl_root == FIXTURE_ROOT / "cursor"
    assert request.gemini_cli_jsonl_root == FIXTURE_ROOT / "gemini_cli"
    assert request.github_copilot_jsonl_root == FIXTURE_ROOT / "github_copilot"
    assert request.end_day_utc == "2026-06-14"
    assert request.started_at == "2026-06-14T00:00:00Z"


def test_primary_refresh_command_payload_from_request_uses_existing_contract():
    connection = memory_connection()
    request = primary_refresh_command_request_from_mapping(
        {
            "codex_jsonl_root": "experiments/fixtures/local_sources/codex",
            "claude_code_jsonl_root": "experiments/fixtures/local_sources/claude_code",
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z",
        }
    )

    payload = build_primary_refresh_command_payload_from_request(
        request,
        connection=connection,
    )

    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570


def test_primary_refresh_command_response_from_mapping_returns_setup_success():
    payload = build_primary_refresh_command_response_from_mapping(
        {
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z",
        }
    )

    assert "error" not in payload
    assert [item["events_seen"] for item in payload["refresh_results"]] == [0, 0, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["event_count"] == 0


def test_primary_refresh_command_response_from_mapping_returns_fixture_success():
    connection = memory_connection()
    payload = build_primary_refresh_command_response_from_mapping(
        {
            "codex_jsonl_root": "experiments/fixtures/local_sources/codex",
            "claude_code_jsonl_root": "experiments/fixtures/local_sources/claude_code",
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z",
        },
        connection=connection,
    )

    assert "error" not in payload
    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570


def test_primary_refresh_command_response_from_json_returns_fixture_success():
    connection = memory_connection()
    payload = build_primary_refresh_command_response_from_json(
        json.dumps(
            {
                "codex_jsonl_root": "experiments/fixtures/local_sources/codex",
                "claude_code_jsonl_root": "experiments/fixtures/local_sources/claude_code",
                "end_day_utc": "2026-06-14",
                "started_at": "2026-06-14T00:00:00Z",
            }
        ),
        connection=connection,
    )

    text = json.dumps(payload, sort_keys=True)
    assert "error" not in payload
    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert "experiments/fixtures" not in text
    assert "local_sources" not in text


def test_primary_refresh_command_response_json_serializes_success_with_newline():
    text = build_primary_refresh_command_response_json(
        json.dumps(
            {
                "end_day_utc": "2026-06-14",
                "started_at": "2026-06-14T00:00:00Z",
            }
        )
    )
    payload = json.loads(text)

    assert text.endswith("\n")
    assert "error" not in payload
    assert payload["storage_summary"]["summary"]["event_count"] == 0


def test_primary_refresh_command_response_from_json_rejects_invalid_json_without_echo():
    payload = build_primary_refresh_command_response_from_json(
        '{"codex_jsonl_root":"C:/Users/example/secret/codex",'
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "message": "refresh request must be valid JSON",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_primary_refresh_command_response_from_json_rejects_non_object():
    payload = build_primary_refresh_command_response_from_json(
        json.dumps(["not", "an", "object"])
    )

    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "message": "refresh request must be a JSON object",
        }
    }


def test_primary_refresh_command_response_from_mapping_returns_redacted_error():
    payload = build_primary_refresh_command_response_from_mapping(
        {
            "codex_jsonl_root": "C:/Users/example/secret/codex",
            "end_day_utc": "2026-6-14",
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_primary_refresh_command_request_rejects_implicit_discovery_fields():
    try:
        primary_refresh_command_request_from_mapping(
            {
                "end_day_utc": "2026-06-14",
                "auto_discover": True,
            }
        )
    except ValueError as exc:
        assert "unsupported refresh command fields" in str(exc)
    else:
        raise AssertionError("expected unsupported refresh command fields")


def test_primary_refresh_command_request_requires_end_day_utc():
    try:
        primary_refresh_command_request_from_mapping({})
    except ValueError as exc:
        assert "end_day_utc is required" in str(exc)
    else:
        raise AssertionError("expected end_day_utc validation error")


def test_primary_refresh_command_request_rejects_invalid_end_day_utc():
    try:
        primary_refresh_command_request_from_mapping(
            {
                "end_day_utc": "2026-6-14",
            }
        )
    except ValueError as exc:
        assert "end_day_utc must be YYYY-MM-DD" in str(exc)
    else:
        raise AssertionError("expected invalid end_day_utc validation error")


def test_primary_refresh_command_request_rejects_invalid_started_at():
    try:
        primary_refresh_command_request_from_mapping(
            {
                "end_day_utc": "2026-06-14",
                "started_at": "not-a-timestamp",
            }
        )
    except ValueError as exc:
        assert "started_at must be ISO-8601" in str(exc)
    else:
        raise AssertionError("expected invalid started_at validation error")


def test_primary_refresh_command_error_payload_is_structured_and_redacted():
    try:
        primary_refresh_command_request_from_mapping(
            {
                "codex_jsonl_root": "C:/Users/example/secret/codex",
                "end_day_utc": "2026-6-14",
            }
        )
    except PrimaryRefreshCommandError as exc:
        payload = primary_refresh_command_error_to_payload(exc)
    else:
        raise AssertionError("expected invalid request error")

    text = json.dumps(payload, sort_keys=True)
    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "field": "end_day_utc",
            "message": "end_day_utc must be YYYY-MM-DD",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_primary_refresh_command_request_rejects_empty_root_strings():
    try:
        primary_refresh_command_request_from_mapping(
            {
                "codex_jsonl_root": "",
                "end_day_utc": "2026-06-14",
            }
        )
    except PrimaryRefreshCommandError as exc:
        assert "codex_jsonl_root must be a non-empty string" in str(exc)
        assert exc.field == "codex_jsonl_root"
    else:
        raise AssertionError("expected empty root validation error")


def test_primary_refresh_command_response_from_mapping_wraps_empty_root_errors():
    payload = build_primary_refresh_command_response_from_mapping(
        {
            "codex_jsonl_root": "C:/Users/example/secret/codex",
            "claude_code_jsonl_root": " ",
            "end_day_utc": "2026-06-14",
        }
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "field": "claude_code_jsonl_root",
            "message": "claude_code_jsonl_root must be a non-empty string when provided",
        }
    }
    assert "C:/Users" not in text
    assert "secret" not in text


def test_primary_refresh_command_response_from_mapping_wraps_non_string_root_errors():
    payload = build_primary_refresh_command_response_from_mapping(
        {
            "codex_jsonl_root": 123,
            "end_day_utc": "2026-06-14",
        }
    )

    assert payload == {
        "error": {
            "code": "invalid_refresh_request",
            "field": "codex_jsonl_root",
            "message": "codex_jsonl_root must be a non-empty string when provided",
        }
    }


def test_primary_refresh_command_payload_uses_explicit_codex_and_claude_roots():
    connection = memory_connection()

    payload = build_primary_refresh_command_payload(
        connection=connection,
        codex_jsonl_root=FIXTURE_ROOT / "codex",
        claude_code_jsonl_root=FIXTURE_ROOT / "claude_code",
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert summary.totals.total_tokens == 7570


def test_primary_refresh_command_payload_uses_all_explicit_usage_import_roots():
    connection = memory_connection()

    payload = build_primary_refresh_command_payload(
        connection=connection,
        codex_jsonl_root=FIXTURE_ROOT / "codex",
        claude_code_jsonl_root=FIXTURE_ROOT / "claude_code",
        cursor_jsonl_root=FIXTURE_ROOT / "cursor",
        gemini_cli_jsonl_root=FIXTURE_ROOT / "gemini_cli",
        github_copilot_jsonl_root=FIXTURE_ROOT / "github_copilot",
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 1, 1, 1]
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 17040
    assert summary.totals.total_tokens == 17040


def test_primary_refresh_command_payload_without_roots_records_setup_only():
    payload = build_primary_refresh_command_payload(
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )

    assert [item["events_seen"] for item in payload["refresh_results"]] == [0, 0, 0, 0, 0]
    assert [item["status"] for item in payload["refresh_results"]] == [
        "setup_required",
        "setup_required",
        "manual_only",
        "setup_required",
        "official_report",
    ]
    assert payload["storage_summary"]["summary"]["event_count"] == 0


def test_primary_refresh_command_payload_does_not_return_source_paths():
    payload = build_primary_refresh_command_payload(
        codex_jsonl_root=FIXTURE_ROOT / "codex",
        claude_code_jsonl_root=FIXTURE_ROOT / "claude_code",
        cursor_jsonl_root=FIXTURE_ROOT / "cursor",
        gemini_cli_jsonl_root=FIXTURE_ROOT / "gemini_cli",
        github_copilot_jsonl_root=FIXTURE_ROOT / "github_copilot",
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )
    text = json.dumps(payload, sort_keys=True)

    assert "experiments/fixtures" not in text
    assert "local_sources" not in text
    for item in payload["refresh_results"]:
        assert "root" not in item
        assert "path" not in item
        assert "file" not in item
