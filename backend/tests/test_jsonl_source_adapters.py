import sqlite3
from pathlib import Path

import pytest

from backend.core import ContractError
from backend.sources import (
    ClaudeCodeJsonlAdapter,
    CodexJsonlAdapter,
    CursorJsonlAdapter,
    GeminiCliTelemetryAdapter,
    GithubCopilotReportAdapter,
    sync_source_adapter,
)
from backend.sources.jsonl_usage import read_usage_jsonl_events
from backend.storage import initialize_schema, list_sources, query_daily_summary


FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_codex_jsonl_adapter_reads_aggregate_fixture_events():
    connection = memory_connection()
    adapter = CodexJsonlAdapter(FIXTURE_ROOT / "codex")

    result = sync_source_adapter(
        connection,
        adapter,
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert result.state.status == "ready"
    assert result.events_seen == 2
    assert summary.event_count == 2
    assert summary.by_source["codex"].total_tokens == 2540
    assert summary.by_source["codex"].cached_input_tokens == 550


def test_claude_jsonl_adapter_reads_cache_read_and_creation_tokens():
    connection = memory_connection()
    adapter = ClaudeCodeJsonlAdapter(FIXTURE_ROOT / "claude_code")

    result = sync_source_adapter(
        connection,
        adapter,
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert result.state.status == "ready"
    assert result.events_seen == 2
    assert summary.event_count == 2
    assert summary.by_source["claude_code"].total_tokens == 5030
    assert summary.by_source["claude_code"].cached_input_tokens == 1050


def test_cursor_jsonl_adapter_reads_explicit_usage_import():
    connection = memory_connection()
    adapter = CursorJsonlAdapter(FIXTURE_ROOT / "cursor")

    result = sync_source_adapter(
        connection,
        adapter,
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert result.state.status == "ready"
    assert result.state.confidence == "local_estimated"
    assert result.events_seen == 1
    assert summary.by_source["cursor"].total_tokens == 3780


def test_gemini_cli_telemetry_adapter_whitelists_token_fields():
    connection = memory_connection()
    adapter = GeminiCliTelemetryAdapter(FIXTURE_ROOT / "gemini_cli")

    result = sync_source_adapter(
        connection,
        adapter,
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")

    assert result.state.status == "ready"
    assert result.events_seen == 1
    assert summary.by_source["gemini_cli"].total_tokens == 2250
    assert summary.by_source["gemini_cli"].input_tokens == 1800
    assert summary.by_source["gemini_cli"].output_tokens == 360
    assert summary.by_source["gemini_cli"].cached_input_tokens == 120
    assert summary.by_source["gemini_cli"].reasoning_output_tokens == 90

    events = adapter.read_events()
    assert events[0].model == "gemini-3-pro"
    assert events[0].session_id is None
    assert events[0].raw_source_ref is None


def test_jsonl_parser_limits_attributes_payload_to_gemini_cli(tmp_path):
    path = tmp_path / "telemetry.log"
    path.write_text(
        (
            '{"timestamp":"2026-06-14T04:00:00Z",'
            '"attributes":{"model":"gemini-3-pro","total_token_count":123,'
            '"prompt_id":"do-not-store"}}'
            "\n"
        ),
        encoding="utf-8",
    )

    cursor_events = read_usage_jsonl_events(
        path,
        source_kind="cursor",
        source_id="cursor:test",
        confidence="local_estimated",
    )
    gemini_events = read_usage_jsonl_events(
        path,
        source_kind="gemini_cli",
        source_id="gemini_cli:test",
        confidence="local_exact",
    )

    assert cursor_events == []
    assert len(gemini_events) == 1
    assert gemini_events[0].model == "gemini-3-pro"
    assert gemini_events[0].total_tokens == 123
    assert gemini_events[0].raw_source_ref is None


def test_github_copilot_report_adapter_reads_official_report_import():
    connection = memory_connection()
    adapter = GithubCopilotReportAdapter(FIXTURE_ROOT / "github_copilot")

    result = sync_source_adapter(
        connection,
        adapter,
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")
    events = adapter.read_events()

    assert result.state.status == "ready"
    assert result.state.confidence == "official"
    assert result.events_seen == 1
    assert summary.by_source["github_copilot"].total_tokens == 3440
    assert events[0].usage_credits == 3.44
    assert events[0].cost_usd == 0.0344


def test_codex_jsonl_parser_reads_observed_payload_info_last_token_usage(tmp_path):
    path = tmp_path / "rollout.jsonl"
    path.write_text(
        (
            '{"timestamp":"2026-06-14T18:24:16Z",'
            '"payload":{"info":{"model":"gpt-5-codex",'
            '"last_token_usage":{"input_tokens":30,"cached_input_tokens":10,'
            '"output_tokens":20,"reasoning_output_tokens":5,"total_tokens":55},'
            '"total_token_usage":{"input_tokens":300,"cached_input_tokens":100,'
            '"output_tokens":200,"reasoning_output_tokens":50,"total_tokens":550}}},'
            '"prompt":"do not store",'
            '"response":"do not store"}'
            "\n"
        ),
        encoding="utf-8",
    )

    events = read_usage_jsonl_events(
        path,
        source_kind="codex",
        source_id="codex:test",
        confidence="local_exact",
    )

    assert len(events) == 1
    assert events[0].model == "gpt-5-codex"
    assert events[0].total_tokens == 55
    assert events[0].cached_input_tokens == 10
    assert events[0].reasoning_output_tokens == 5
    assert events[0].session_id is None
    assert events[0].raw_source_ref is None


def test_claude_jsonl_parser_reads_observed_message_usage(tmp_path):
    path = tmp_path / "conversation.jsonl"
    path.write_text(
        (
            '{"timestamp":"2026-06-14T18:31:00Z",'
            '"message":{"model":"claude-sonnet-4.6",'
            '"usage":{"input_tokens":40,"cache_read_input_tokens":6,'
            '"cache_creation_input_tokens":4,"output_tokens":12}},'
            '"content":"do not store"}'
            "\n"
        ),
        encoding="utf-8",
    )

    events = read_usage_jsonl_events(
        path,
        source_kind="claude_code",
        source_id="claude_code:test",
        confidence="local_exact",
    )

    assert len(events) == 1
    assert events[0].model == "claude-sonnet-4.6"
    assert events[0].total_tokens == 52
    assert events[0].cached_input_tokens == 10
    assert events[0].session_id is None
    assert events[0].raw_source_ref is None


def test_missing_jsonl_source_records_not_found_without_events(tmp_path):
    connection = memory_connection()
    adapter = CodexJsonlAdapter(tmp_path / "missing")

    result = sync_source_adapter(
        connection,
        adapter,
        started_at="2026-06-14T00:00:00Z",
    )
    sources = list_sources(connection)
    summary = query_daily_summary(connection, "2026-06-14")

    assert result.state.status == "not_found"
    assert result.events_seen == 0
    assert sources[0]["status"] == "not_found"
    assert sources[0]["confidence"] == "unavailable"
    assert summary.event_count == 0


def test_jsonl_parser_ignores_prompt_response_and_session_fields(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text(
        (
            '{"timestamp":"2026-06-14T00:00:00Z",'
            '"session_id":"not-stored",'
            '"prompt":"do not store",'
            '"response":"do not store",'
            '"tool_output":"do not store",'
            '"usage":{"input_tokens":10,"output_tokens":5,"total_tokens":15}}'
            "\n"
        ),
        encoding="utf-8",
    )

    events = read_usage_jsonl_events(
        path,
        source_kind="codex",
        source_id="codex:test",
        confidence="local_exact",
    )

    assert len(events) == 1
    assert events[0].session_id is None
    assert events[0].workspace_id is None
    assert events[0].raw_source_ref is None
    assert events[0].total_tokens == 15


def test_jsonl_parser_rejects_invalid_jsonl_record(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{bad json\n", encoding="utf-8")

    with pytest.raises(ContractError):
        read_usage_jsonl_events(
            path,
            source_kind="codex",
            source_id="codex:test",
            confidence="local_exact",
        )
