import sqlite3
from pathlib import Path

import pytest

from backend.core import ContractError
from backend.sources import (
    JsonlSourceCandidate,
    discover_jsonl_source,
    discover_jsonl_sources,
    sync_source_adapter,
)
from backend.storage import initialize_schema, query_daily_summary


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_explicit_jsonl_discovery_returns_ready_codex_and_claude_adapters():
    discovered = discover_jsonl_sources(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    assert [item.source_kind for item in discovered] == ["codex", "claude_code"]
    assert [item.state.status for item in discovered] == ["ready", "ready"]
    assert [item.state.confidence for item in discovered] == ["local_exact", "local_exact"]


def test_discovered_ready_adapters_sync_aggregate_usage():
    connection = memory_connection()
    discovered = discover_jsonl_sources(
        [
            JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex"),
            JsonlSourceCandidate("claude_code", FIXTURE_ROOT / "claude_code"),
        ]
    )

    for item in discovered:
        result = sync_source_adapter(
            connection,
            item.adapter,
            started_at="2026-06-14T00:00:00Z",
        )
        assert result.state.status == "ready"

    summary = query_daily_summary(connection, "2026-06-14")

    assert summary.event_count == 4
    assert summary.totals.total_tokens == 7570
    assert summary.by_source["codex"].total_tokens == 2540
    assert summary.by_source["claude_code"].total_tokens == 5030


def test_explicit_jsonl_discovery_reports_missing_and_setup_required(tmp_path):
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    missing = discover_jsonl_source(
        JsonlSourceCandidate("codex", tmp_path / "missing")
    )
    setup_required = discover_jsonl_source(
        JsonlSourceCandidate("claude_code", empty_root)
    )

    assert missing.state.status == "not_found"
    assert missing.state.confidence == "unavailable"
    assert setup_required.state.status == "setup_required"
    assert setup_required.state.confidence == "unavailable"


def test_explicit_jsonl_discovery_preserves_custom_source_id():
    discovered = discover_jsonl_source(
        JsonlSourceCandidate(
            "codex",
            FIXTURE_ROOT / "codex",
            source_id="codex:portable-fixture",
        )
    )

    assert discovered.source_id == "codex:portable-fixture"
    assert discovered.state.source_id == "codex:portable-fixture"


def test_explicit_jsonl_discovery_supports_usage_import_sources():
    discovered = {
        item.source_kind: item
        for item in discover_jsonl_sources(
            [
                JsonlSourceCandidate("cursor", FIXTURE_ROOT / "cursor"),
                JsonlSourceCandidate("gemini_cli", FIXTURE_ROOT / "gemini_cli"),
                JsonlSourceCandidate("github_copilot", FIXTURE_ROOT / "github_copilot"),
            ]
        )
    }

    assert discovered["cursor"].state.status == "ready"
    assert discovered["cursor"].state.confidence == "local_estimated"
    assert discovered["gemini_cli"].state.status == "ready"
    assert discovered["github_copilot"].state.status == "ready"
    assert discovered["github_copilot"].state.confidence == "official"


def test_explicit_jsonl_discovery_rejects_unknown_sources_without_adapter():
    with pytest.raises(ContractError, match="does not have a supported"):
        discover_jsonl_source(
            JsonlSourceCandidate("unknown_source", FIXTURE_ROOT / "gemini_cli")
        )


def test_explicit_jsonl_candidate_rejects_blank_source_id():
    with pytest.raises(ContractError, match="must not be blank"):
        JsonlSourceCandidate("codex", FIXTURE_ROOT / "codex", source_id=" ")
