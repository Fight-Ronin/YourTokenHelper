import sqlite3
from pathlib import Path

from backend.sources import (
    JsonlSourceCandidate,
    build_primary_source_adapters,
    refresh_results_to_payload,
    refresh_source_adapters,
    refresh_sources_summary_payload,
)
from backend.storage import initialize_schema, list_sources, query_daily_summary


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def sync_run_count(connection):
    row = connection.execute("SELECT COUNT(*) AS count FROM sync_runs").fetchone()
    return int(row["count"])


def test_refresh_source_adapters_records_results_for_primary_registry():
    connection = memory_connection()
    adapters = build_primary_source_adapters(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    results = refresh_source_adapters(
        connection,
        adapters,
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")
    source_statuses = {
        item["source_kind"]: item["status"]
        for item in list_sources(connection)
    }

    assert [result.events_seen for result in results] == [2, 2, 0, 0, 0]
    assert [result.state.status for result in results] == [
        "ready",
        "ready",
        "manual_only",
        "setup_required",
        "official_report",
    ]
    assert sync_run_count(connection) == 5
    assert summary.event_count == 4
    assert summary.totals.total_tokens == 7570
    assert source_statuses == {
        "codex": "ready",
        "claude_code": "ready",
        "cursor": "manual_only",
        "gemini_cli": "setup_required",
        "github_copilot": "official_report",
    }


def test_refresh_results_payload_is_ui_ready_without_source_paths():
    connection = memory_connection()
    adapters = build_primary_source_adapters(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    results = refresh_source_adapters(
        connection,
        adapters,
        started_at="2026-06-14T00:00:00Z",
    )
    payload = refresh_results_to_payload(results)

    assert [item["source_kind"] for item in payload] == [
        "codex",
        "claude_code",
        "cursor",
        "gemini_cli",
        "github_copilot",
    ]
    assert payload[0] == {
        "source_kind": "codex",
        "source_id": "codex:local_jsonl",
        "status": "ready",
        "confidence": "local_exact",
        "events_seen": 2,
        "sync_run_id": 1,
        "message": "Aggregate JSONL usage files are available.",
    }
    assert payload[2]["status"] == "manual_only"
    assert payload[2]["events_seen"] == 0
    for item in payload:
        assert "root" not in item
        assert "path" not in item
        assert "file" not in item


def test_refresh_sources_summary_payload_combines_refresh_results_and_summary():
    connection = memory_connection()
    adapters = build_primary_source_adapters(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    payload = refresh_sources_summary_payload(
        connection,
        adapters,
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )

    assert list(payload) == ["refresh_results", "storage_summary"]
    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 0, 0, 0]
    assert payload["storage_summary"]["generated_from"] == "backend.sources.refresh"
    assert payload["storage_summary"]["summary"]["event_count"] == 4
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert payload["storage_summary"]["source_states"] == [
        {"source_kind": "codex", "status": "ready", "confidence": "local_exact"},
        {"source_kind": "claude_code", "status": "ready", "confidence": "local_exact"},
        {"source_kind": "cursor", "status": "manual_only", "confidence": "manual"},
        {"source_kind": "gemini_cli", "status": "setup_required", "confidence": "unavailable"},
        {"source_kind": "github_copilot", "status": "official_report", "confidence": "official"},
    ]


def test_refresh_sources_summary_payload_replaces_current_window_instead_of_accumulating():
    connection = memory_connection()
    adapters = build_primary_source_adapters(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    first = refresh_sources_summary_payload(
        connection,
        adapters,
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )
    second = refresh_sources_summary_payload(
        connection,
        adapters,
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:01:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert first["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert second["storage_summary"]["summary"]["totals"]["total_tokens"] == 7570
    assert summary.event_count == 4
    assert summary.totals.total_tokens == 7570
    assert sync_run_count(connection) == 10


def test_refresh_sources_summary_payload_without_roots_keeps_summary_empty():
    connection = memory_connection()

    payload = refresh_sources_summary_payload(
        connection,
        build_primary_source_adapters(),
        end_day_utc="2026-06-14",
        started_at="2026-06-14T00:00:00Z",
    )

    assert [item["events_seen"] for item in payload["refresh_results"]] == [0, 0, 0, 0, 0]
    assert payload["storage_summary"]["summary"]["event_count"] == 0
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 0
    assert len(payload["storage_summary"]["source_states"]) == 5


def test_refresh_source_adapters_without_roots_records_setup_states_only():
    connection = memory_connection()

    results = refresh_source_adapters(
        connection,
        build_primary_source_adapters(),
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert [result.events_seen for result in results] == [0, 0, 0, 0, 0]
    assert sync_run_count(connection) == 5
    assert summary.event_count == 0


def test_refresh_source_adapters_accepts_empty_adapter_list():
    connection = memory_connection()

    assert refresh_source_adapters(connection, []) == []
    assert sync_run_count(connection) == 0
    assert query_daily_summary(connection, "2026-06-14").event_count == 0
