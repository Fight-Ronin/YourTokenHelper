import pytest

from backend.core import (
    API_COST_SOURCE_KINDS,
    AllowanceWindow,
    ContractError,
    UsageEvent,
    aggregate_usage,
    allowance_window_to_dict,
    usage_summary_to_dict,
)


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


def test_usage_event_request_count_defaults_to_one_and_aggregates():
    default_event = UsageEvent(
        source_kind="codex",
        source_id="codex:fixture",
        started_at="2026-06-14T00:00:00Z",
        total_tokens=1,
        confidence="local_exact",
    )
    grouped_event = UsageEvent(
        source_kind="openai_api_cost",
        source_id="openai_api_cost:admin_api",
        started_at="2026-06-14T01:00:00Z",
        total_tokens=100,
        confidence="official",
        request_count=42,
    )

    assert default_event.request_count == 1
    assert aggregate_usage([default_event, grouped_event]).event_count == 43

    with pytest.raises(ContractError):
        UsageEvent(
            source_kind="codex",
            source_id="codex:fixture",
            started_at="2026-06-14T00:00:00Z",
            total_tokens=1,
            confidence="local_exact",
            request_count=-1,
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
    assert summary.by_day_source["2026-06-07"]["codex"].total_tokens == 15
    assert summary.by_day_source["2026-06-14"]["codex"].total_tokens == 140
    assert summary.by_day_source["2026-06-14"]["claude_code"].total_tokens == 260
    assert summary.rolling_7d.window_start == "2026-06-08"
    assert summary.rolling_7d.window_end == "2026-06-14"
    assert summary.rolling_7d.totals.total_tokens == 400


@pytest.mark.parametrize("source_kind", API_COST_SOURCE_KINDS)
def test_api_cost_sources_are_secondary_without_required_cost_totaling(source_kind):
    event = UsageEvent(
        source_kind=source_kind,
        source_id=f"{source_kind}:fixture",
        started_at="2026-06-14T00:00:00Z",
        total_tokens=43100,
        confidence="official",
        cost_usd=1.03,
        api_key_id="api-key_hash",
    )

    assert event.cost_usd == 1.03
    assert event.api_key_id == "api-key_hash"
    assert aggregate_usage([event]).totals.total_tokens == 43100


def test_allowance_window_preserves_api_backed_remaining_and_reset_state():
    window = AllowanceWindow(
        source_kind="codex",
        source_id="codex:fixture",
        status="api_backed",
        unit="tokens",
        window_start="2026-06-14T00:00:00+08:00",
        window_end="2026-06-21T00:00:00+08:00",
        reset_at="2026-06-21T00:00:00+08:00",
        limit_amount=100000,
        used_amount=25000,
        remaining_amount=75000,
    )

    assert window.window_start == "2026-06-13T16:00:00Z"
    assert window.window_end == "2026-06-20T16:00:00Z"
    assert window.reset_at == "2026-06-20T16:00:00Z"
    assert window.remaining_amount == 75000


def test_allowance_window_can_represent_manual_or_derived_data_without_exactness_loss():
    manual = AllowanceWindow(
        source_kind="claude_code",
        source_id="claude_code:fixture",
        status="manual",
        unit="credits",
        used_amount=12.5,
        remaining_amount=37.5,
        note="Entered by the user.",
    )
    derived = AllowanceWindow(
        source_kind="github_copilot",
        source_id="github_copilot:fixture",
        status="derived",
        unit="requests",
        used_amount=20,
        remaining_amount=80,
    )

    assert manual.status == "manual"
    assert manual.unit == "credits"
    assert derived.status == "derived"
    assert derived.unit == "requests"


def test_unavailable_allowance_does_not_accept_fake_remaining_or_reset_data():
    unavailable = AllowanceWindow(
        source_kind="cursor",
        source_id="cursor:fixture",
        status="unavailable",
        unit="unknown",
        used_amount=0,
        note="No local allowance source observed.",
    )

    assert unavailable.remaining_amount is None
    assert unavailable.reset_at is None

    with pytest.raises(ContractError):
        AllowanceWindow(
            source_kind="cursor",
            source_id="cursor:fixture",
            status="unavailable",
            unit="unknown",
            remaining_amount=0,
        )


def test_usage_summary_serializes_to_plain_mock_ui_shape():
    summary = aggregate_usage(
        [
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
    )

    payload = usage_summary_to_dict(summary)

    assert payload == {
        "event_count": 2,
        "totals": {
            "input_tokens": 300,
            "output_tokens": 100,
            "cached_input_tokens": 50,
            "reasoning_output_tokens": 3,
            "total_tokens": 400,
        },
        "by_source": {
            "claude_code": {
                "input_tokens": 200,
                "output_tokens": 60,
                "cached_input_tokens": 30,
                "reasoning_output_tokens": 0,
                "total_tokens": 260,
            },
            "codex": {
                "input_tokens": 100,
                "output_tokens": 40,
                "cached_input_tokens": 20,
                "reasoning_output_tokens": 3,
                "total_tokens": 140,
            },
        },
        "by_day": {
            "2026-06-14": {
                "input_tokens": 300,
                "output_tokens": 100,
                "cached_input_tokens": 50,
                "reasoning_output_tokens": 3,
                "total_tokens": 400,
            },
        },
        "by_day_source": {
            "2026-06-14": {
                "claude_code": {
                    "input_tokens": 200,
                    "output_tokens": 60,
                    "cached_input_tokens": 30,
                    "reasoning_output_tokens": 0,
                    "total_tokens": 260,
                },
                "codex": {
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "cached_input_tokens": 20,
                    "reasoning_output_tokens": 3,
                    "total_tokens": 140,
                },
            },
        },
        "rolling_7d": {
            "window_start": "2026-06-08",
            "window_end": "2026-06-14",
            "totals": {
                "input_tokens": 300,
                "output_tokens": 100,
                "cached_input_tokens": 50,
                "reasoning_output_tokens": 3,
                "total_tokens": 400,
            },
        },
    }


def test_allowance_window_serialization_omits_unavailable_fake_remaining_data():
    payload = allowance_window_to_dict(
        AllowanceWindow(
            source_kind="cursor",
            source_id="cursor:fixture",
            status="unavailable",
            unit="unknown",
            used_amount=0,
            note="No local allowance source observed.",
        )
    )

    assert payload == {
        "source_kind": "cursor",
        "source_id": "cursor:fixture",
        "status": "unavailable",
        "unit": "unknown",
        "used_amount": 0,
        "note": "No local allowance source observed.",
    }
    assert "remaining_amount" not in payload
    assert "reset_at" not in payload
