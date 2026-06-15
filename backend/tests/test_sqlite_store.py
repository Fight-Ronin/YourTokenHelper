import sqlite3

import pytest

from backend.core import AllowanceWindow, ContractError, UsageEvent
from backend.fixtures.mock_summary import mock_allowance_windows, mock_usage_events
from backend.storage import (
    CostBucketRecord,
    clear_aggregate_cache,
    initialize_schema,
    list_sources,
    query_allowance_windows,
    query_cost_total_usd,
    query_daily_summary,
    query_daily_trend,
    query_refresh_state,
    query_rolling_7d_summary,
    query_usage_breakdown,
    record_cost_records,
    record_sync_run,
    record_usage_events,
    replace_allowance_windows,
    upsert_source,
)


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_schema_initializes_required_tables():
    connection = memory_connection()

    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    assert {
        "sources",
        "usage_buckets",
        "cost_buckets",
        "allowance_windows",
        "sync_runs",
    }.issubset(tables)


def test_fixture_seed_queries_daily_and_rolling_weekly_summaries():
    connection = memory_connection()
    old_event = UsageEvent(
        source_kind="codex",
        source_id="codex:mock",
        started_at="2026-06-07T12:00:00Z",
        input_tokens=90,
        output_tokens=10,
        total_tokens=100,
        confidence="local_exact",
    )

    record_usage_events(connection, [old_event, *mock_usage_events()])

    daily = query_daily_summary(connection, "2026-06-14")
    weekly = query_rolling_7d_summary(connection, "2026-06-14")

    assert daily.event_count == 6
    assert daily.totals.total_tokens == 60140
    assert daily.by_source["codex"].total_tokens == 2540
    assert daily.by_day["2026-06-14"].total_tokens == 60140
    assert daily.by_day_source["2026-06-14"]["codex"].total_tokens == 2540
    assert weekly.event_count == 6
    assert weekly.totals.total_tokens == 60140
    assert weekly.by_day_source["2026-06-14"]["codex"].total_tokens == 2540
    assert weekly.rolling_7d.window_start == "2026-06-08"
    assert weekly.rolling_7d.window_end == "2026-06-14"
    assert "2026-06-07" not in weekly.by_day


def test_daily_trend_zero_fills_missing_days():
    connection = memory_connection()
    record_usage_events(connection, mock_usage_events())

    trend = query_daily_trend(connection, "2026-06-14")

    assert list(trend) == [
        "2026-06-08",
        "2026-06-09",
        "2026-06-10",
        "2026-06-11",
        "2026-06-12",
        "2026-06-13",
        "2026-06-14",
    ]
    assert trend["2026-06-08"].total_tokens == 0
    assert trend["2026-06-14"].total_tokens == 60140


def test_allowance_windows_preserve_unavailable_without_fake_remaining():
    connection = memory_connection()

    replace_allowance_windows(connection, mock_allowance_windows())
    windows = {
        window.source_kind: window
        for window in query_allowance_windows(connection)
    }

    assert windows["codex"].remaining_amount == 97460
    assert windows["cursor"].status == "unavailable"
    assert windows["cursor"].remaining_amount is None
    assert windows["cursor"].reset_at is None

    with pytest.raises(ContractError):
        replace_allowance_windows(
            connection,
            [
                AllowanceWindow(
                    source_kind="cursor",
                    source_id="cursor:mock",
                    status="unavailable",
                    unit="unknown",
                    remaining_amount=0,
                )
            ],
        )


def test_cost_queries_return_none_when_cost_data_is_unavailable():
    connection = memory_connection()
    record_usage_events(connection, mock_usage_events())

    assert query_cost_total_usd(connection, "2026-06-14", "2026-06-14") == pytest.approx(1.03)
    assert query_cost_total_usd(connection, "2026-06-13", "2026-06-13") is None


def test_cost_records_do_not_count_as_usage_events():
    connection = memory_connection()

    record_cost_records(
        connection,
        [
            CostBucketRecord(
                day_utc="2026-06-14",
                source_kind="openai_api_cost",
                source_id="openai_api_cost:admin_api",
                project_id="project_hash",
                api_key_id="api_key_hash",
                cost_usd=1.25,
            )
        ],
    )

    assert query_daily_summary(connection, "2026-06-14").event_count == 0
    assert query_cost_total_usd(connection, "2026-06-14", "2026-06-14") == pytest.approx(1.25)
    assert list_sources(connection)[0]["source_kind"] == "openai_api_cost"

    with pytest.raises(ContractError):
        CostBucketRecord(
            day_utc="2026-06-14",
            source_kind="openai_api_cost",
            source_id="openai_api_cost:admin_api",
            cost_usd=True,
        )
    with pytest.raises(ContractError):
        CostBucketRecord(
            day_utc="2026-06-14",
            source_kind="openai_api_cost",
            source_id="openai_api_cost:admin_api",
            cost_usd=1.25,
            currency=None,
        )


def test_refresh_state_reports_never_refreshed_before_sync_runs():
    connection = memory_connection()

    assert query_refresh_state(connection) == {
        "last_attempt_at": None,
        "last_success_at": None,
        "last_status": "never_refreshed",
        "successful_source_count": 0,
        "attempted_source_count": 0,
        "events_seen": 0,
    }


def test_refresh_state_uses_latest_sync_run_per_source():
    connection = memory_connection()
    record_sync_run(
        connection,
        source_kind="codex",
        source_id="codex:local_jsonl",
        status="ready",
        started_at="2026-06-14T00:00:00Z",
        events_seen=2,
    )
    record_sync_run(
        connection,
        source_kind="claude_code",
        source_id="claude_code:local_jsonl",
        status="permission_denied",
        started_at="2026-06-14T00:01:00Z",
        events_seen=0,
    )
    record_sync_run(
        connection,
        source_kind="claude_code",
        source_id="claude_code:local_jsonl",
        status="ready",
        started_at="2026-06-14T00:02:00Z",
        events_seen=3,
    )

    assert query_refresh_state(connection) == {
        "last_attempt_at": "2026-06-14T00:02:00Z",
        "last_success_at": "2026-06-14T00:02:00Z",
        "last_status": "succeeded",
        "successful_source_count": 2,
        "attempted_source_count": 2,
        "events_seen": 5,
    }


def test_usage_breakdowns_cover_api_key_model_and_project():
    connection = memory_connection()
    record_usage_events(
        connection,
        [
            UsageEvent(
                source_kind="openai_api_cost",
                source_id="openai_api_cost:test",
                started_at="2026-06-14T01:00:00Z",
                input_tokens=70,
                output_tokens=30,
                total_tokens=100,
                confidence="official",
                model="gpt-5.5",
                project_id="project_a",
                api_key_id="key_a",
                cost_usd=0.01,
            ),
            UsageEvent(
                source_kind="openai_api_cost",
                source_id="openai_api_cost:test",
                started_at="2026-06-14T02:00:00Z",
                input_tokens=140,
                output_tokens=60,
                total_tokens=200,
                confidence="official",
                model="gpt-5.5",
                project_id="project_b",
                api_key_id="key_b",
                cost_usd=0.02,
            ),
        ],
    )

    by_key = query_usage_breakdown(
        connection,
        "2026-06-14",
        "2026-06-14",
        dimension="api_key_id",
    )
    by_model = query_usage_breakdown(
        connection,
        "2026-06-14",
        "2026-06-14",
        dimension="model",
    )
    by_project = query_usage_breakdown(
        connection,
        "2026-06-14",
        "2026-06-14",
        dimension="project_id",
    )

    assert by_key["key_a"].total_tokens == 100
    assert by_key["key_b"].total_tokens == 200
    assert by_model["gpt-5.5"].total_tokens == 300
    assert by_project["project_a"].total_tokens == 100
    assert by_project["project_b"].total_tokens == 200

    with pytest.raises(ContractError):
        query_usage_breakdown(
            connection,
            "2026-06-14",
            "2026-06-14",
            dimension="session_id",
        )


def test_clear_aggregate_cache_keeps_source_settings():
    connection = memory_connection()
    upsert_source(
        connection,
        source_kind="codex",
        source_id="codex:mock",
        confidence="local_exact",
        status="ready",
        is_enabled=False,
    )
    record_usage_events(connection, mock_usage_events())
    replace_allowance_windows(connection, mock_allowance_windows())
    record_sync_run(
        connection,
        source_kind="codex",
        source_id="codex:mock",
        status="ok",
        started_at="2026-06-14T00:00:00Z",
        finished_at="2026-06-14T00:01:00Z",
        events_seen=6,
    )

    clear_aggregate_cache(connection)

    assert query_daily_summary(connection, "2026-06-14").event_count == 0
    assert query_cost_total_usd(connection, "2026-06-14", "2026-06-14") is None
    assert query_allowance_windows(connection) == []
    sources = {
        source["source_id"]: source
        for source in list_sources(connection)
    }
    assert set(sources) == {
        "claude_code:mock",
        "codex:mock",
        "cursor:mock",
        "gemini_cli:mock",
        "github_copilot:mock",
        "openai_api_cost:mock",
    }
    assert sources["codex:mock"] == {
        "source_kind": "codex",
        "source_id": "codex:mock",
        "display_name": None,
        "status": "ready",
        "confidence": "local_exact",
        "is_enabled": False,
    }
