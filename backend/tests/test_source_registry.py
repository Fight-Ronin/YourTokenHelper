import sqlite3
from pathlib import Path

import pytest

from backend.core import ContractError
from backend.sources import (
    JsonlSourceCandidate,
    build_primary_source_adapters,
    setup_status_adapter,
    sync_source_adapter,
)
from backend.storage import initialize_schema, list_sources, query_daily_summary


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def states_for(adapters):
    return {
        adapter.get_state().source_kind: adapter.get_state()
        for adapter in adapters
    }


def test_primary_source_registry_returns_status_for_all_primary_sources_without_roots():
    states = states_for(build_primary_source_adapters())

    assert list(states) == [
        "codex",
        "claude_code",
        "cursor",
        "gemini_cli",
        "github_copilot",
    ]
    assert states["codex"].status == "setup_required"
    assert states["claude_code"].status == "setup_required"
    assert states["cursor"].status == "manual_only"
    assert states["gemini_cli"].status == "setup_required"
    assert states["github_copilot"].status == "official_report"


def test_primary_source_registry_uses_explicit_codex_and_claude_jsonl_roots():
    states = states_for(
        build_primary_source_adapters(
            [
                JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
                JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
            ]
        )
    )

    assert states["codex"].status == "ready"
    assert states["claude_code"].status == "ready"
    assert states["cursor"].status == "manual_only"
    assert states["gemini_cli"].status == "setup_required"
    assert states["github_copilot"].status == "official_report"


def test_primary_source_registry_syncs_ready_sources_and_records_manual_states():
    connection = memory_connection()
    adapters = build_primary_source_adapters(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    results = [
        sync_source_adapter(
            connection,
            adapter,
            started_at="2026-06-14T00:00:00Z",
        )
        for adapter in adapters
    ]
    summary = query_daily_summary(connection, "2026-06-14")
    source_statuses = {
        item["source_kind"]: item["status"]
        for item in list_sources(connection)
    }

    assert [result.events_seen for result in results] == [2, 2, 0, 0, 0]
    assert summary.event_count == 4
    assert summary.totals.total_tokens == 7570
    assert source_statuses == {
        "codex": "ready",
        "claude_code": "ready",
        "cursor": "manual_only",
        "gemini_cli": "setup_required",
        "github_copilot": "official_report",
    }


def test_primary_source_registry_without_roots_does_not_record_usage_events():
    connection = memory_connection()

    for adapter in build_primary_source_adapters():
        sync_source_adapter(
            connection,
            adapter,
            started_at="2026-06-14T00:00:00Z",
        )

    summary = query_daily_summary(connection, "2026-06-14")
    source_statuses = {
        item["source_kind"]: item["status"]
        for item in list_sources(connection)
    }

    assert summary.event_count == 0
    assert source_statuses["codex"] == "setup_required"
    assert source_statuses["claude_code"] == "setup_required"
    assert source_statuses["cursor"] == "manual_only"


def test_setup_status_adapter_rejects_unknown_source_kind():
    with pytest.raises(ContractError, match="Unsupported primary source"):
        setup_status_adapter("openai_api_cost")
