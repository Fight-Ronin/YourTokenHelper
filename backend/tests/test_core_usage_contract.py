import pytest

from backend.core import ContractError, UsageEvent, aggregate_usage


def test_usage_event_normalizes_utc_timestamp_and_preserves_missing_optional_data():
    event = UsageEvent(
        source_kind="codex",
        source_id="codex:fixture",
        started_at="2026-06-14T12:00:00+08:00",
        input_tokens=100,
        output_tokens=25,
        total_tokens=125,
        confidence="local_exact",
    )

    assert event.started_at == "2026-06-14T04:00:00Z"
    assert event.day_utc == "2026-06-14"
    assert event.cost_usd is None
    assert event.raw_source_ref is None


def test_usage_event_rejects_unknown_source_and_negative_tokens():
    with pytest.raises(ContractError):
        UsageEvent(
            source_kind="unknown_agent",
            source_id="unknown:fixture",
            started_at="2026-06-14T00:00:00Z",
            total_tokens=1,
            confidence="local_exact",
        )

    with pytest.raises(ContractError):
        UsageEvent(
            source_kind="codex",
            source_id="codex:fixture",
            started_at="2026-06-14T00:00:00Z",
            total_tokens=-1,
            confidence="local_exact",
        )


def test_aggregate_usage_builds_daily_source_and_rolling_weekly_totals():
    events = [
        UsageEvent(
            source_kind="codex",
            source_id="codex:fixture",
            started_at="2026-06-07T23:00:00Z",
            input_tokens=10,
            output_tokens=5,
            cached_input_tokens=2,
            reasoning_output_tokens=1,
            total_tokens=15,
            confidence="local_exact",
        ),
        UsageEvent(
            source_kind="codex",
            source_id="codex:fixture",
            started_at="2026-06-14T02:00:00Z",
            input_tokens=100,
            output_tokens=40,
            cached_input_tokens=20,
            reasoning_output_tokens=3,
            total_tokens=140,
            confidence="local_exact",
        ),
        UsageEvent(
            source_kind="claude_code",
            source_id="claude_code:fixture",
            started_at="2026-06-14T03:00:00Z",
            input_tokens=200,
            output_tokens=60,
            cached_input_tokens=30,
            total_tokens=260,
            confidence="local_exact",
        ),
    ]

    summary = aggregate_usage(events)

    assert summary.event_count == 3
    assert summary.totals.total_tokens == 415
    assert summary.totals.cached_input_tokens == 52
    assert summary.by_source["codex"].total_tokens == 155
    assert summary.by_source["claude_code"].total_tokens == 260
    assert summary.by_day["2026-06-14"].total_tokens == 400
    assert summary.rolling_7d.window_start == "2026-06-08"
    assert summary.rolling_7d.window_end == "2026-06-14"
    assert summary.rolling_7d.totals.total_tokens == 400


def test_openai_api_cost_is_secondary_source_without_required_cost_totaling():
    event = UsageEvent(
        source_kind="openai_api_cost",
        source_id="openai_api_cost:fixture",
        started_at="2026-06-14T00:00:00Z",
        total_tokens=43100,
        confidence="official",
        cost_usd=1.03,
        api_key_id="api-key_hash",
    )

    assert event.cost_usd == 1.03
    assert event.api_key_id == "api-key_hash"
    assert aggregate_usage([event]).totals.total_tokens == 43100
