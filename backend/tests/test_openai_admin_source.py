import json
import sqlite3
from pathlib import Path

from backend.core import ContractError
from backend.sources import (
    OPENAI_ADMIN_SOURCE_ID,
    openai_admin_cost_records_from_payload,
    openai_admin_usage_events_from_payload,
    sync_openai_admin_usage_cost_payload,
)
from backend.storage import (
    build_storage_summary_payload,
    initialize_schema,
    list_sources,
    query_allowance_windows,
    query_cost_total_usd,
    query_rolling_7d_summary,
    query_usage_breakdown,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_probe_response.json")


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_openai_admin_fixture_payload_maps_usage_and_costs_without_raw_ids():
    payload = fixture_payload()

    usage_events = openai_admin_usage_events_from_payload(payload)
    cost_records = openai_admin_cost_records_from_payload(payload)

    assert len(usage_events) == 3
    assert sum(event.total_tokens for event in usage_events) == 43100
    assert sum(event.cached_input_tokens or 0 for event in usage_events) == 8900
    assert sum(event.request_count for event in usage_events) == 109
    assert usage_events[0].source_id == OPENAI_ADMIN_SOURCE_ID
    assert usage_events[0].confidence == "official"
    assert usage_events[0].api_key_id.startswith("api-key_")
    assert usage_events[0].project_id.startswith("project_")
    assert "key_fixture" not in json.dumps([event.api_key_id for event in usage_events])
    assert "proj_fixture" not in json.dumps([event.project_id for event in usage_events])

    assert len(cost_records) == 2
    assert sum(record.cost_usd for record in cost_records) == 1.03


def test_openai_admin_usage_preserves_explicit_zero_request_count():
    payload = {
        "usage": {
            "data": [
                {
                    "start_time": 1781222400,
                    "results": [
                        {
                            "input_tokens": 10,
                            "output_tokens": 2,
                            "num_model_requests": 0,
                        }
                    ],
                }
            ]
        }
    }

    events = openai_admin_usage_events_from_payload(payload)

    assert len(events) == 1
    assert events[0].request_count == 0


def test_openai_admin_payload_syncs_usage_costs_and_source_health():
    connection = memory_connection()

    result = sync_openai_admin_usage_cost_payload(
        connection,
        fixture_payload(),
        end_day_utc="2026-06-13",
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_rolling_7d_summary(connection, "2026-06-13")
    by_key = query_usage_breakdown(
        connection,
        "2026-06-12",
        "2026-06-13",
        dimension="api_key_id",
    )
    storage_payload = build_storage_summary_payload(connection, end_day_utc="2026-06-13")

    assert result.state.status == "ready"
    assert result.usage_events_seen == 3
    assert result.cost_records_seen == 2
    assert summary.event_count == 109
    assert summary.by_source["openai_api_cost"].total_tokens == 43100
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") == 1.03
    assert query_allowance_windows(connection) == []
    assert all(label.startswith("api-key_") for label in by_key)
    assert "key_fixture" not in " ".join(by_key)
    assert "key_fixture" not in json.dumps(storage_payload)
    assert "proj_fixture" not in json.dumps(storage_payload)
    assert storage_payload["source_states"] == [
        {
            "source_kind": "openai_api_cost",
            "status": "ready",
            "confidence": "official",
        }
    ]


def test_openai_admin_sync_rejects_missing_endpoint_envelopes_before_replacement():
    connection = memory_connection()
    sync_openai_admin_usage_cost_payload(
        connection,
        fixture_payload(),
        end_day_utc="2026-06-13",
        started_at="2026-06-14T00:00:00Z",
    )

    try:
        sync_openai_admin_usage_cost_payload(
            connection,
            {},
            end_day_utc="2026-06-13",
            started_at="2026-06-14T01:00:00Z",
        )
    except ContractError as exc:
        assert "OpenAI Admin usage endpoint payload is required" in str(exc)
    else:
        raise AssertionError("expected missing endpoint envelope to fail")

    summary = query_rolling_7d_summary(connection, "2026-06-13")
    assert summary.event_count == 109
    assert summary.by_source["openai_api_cost"].total_tokens == 43100
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") == 1.03


def test_openai_admin_permission_denied_records_recoverable_source_state():
    connection = memory_connection()
    payload = {
        "usage": {"error": {"status": 403, "body": {"error": {"code": "missing_scope"}}}},
        "costs": {"error": {"status": 403, "body": {"error": {"code": "missing_scope"}}}},
    }

    result = sync_openai_admin_usage_cost_payload(
        connection,
        payload,
        end_day_utc="2026-06-13",
        started_at="2026-06-14T00:00:00Z",
    )

    assert result.state.status == "permission_denied"
    assert result.state.confidence == "unavailable"
    assert result.usage_events_seen == 0
    assert result.cost_records_seen == 0
    assert query_rolling_7d_summary(connection, "2026-06-13").event_count == 0
    assert list_sources(connection)[0]["status"] == "permission_denied"


def test_openai_admin_sync_keeps_usage_when_costs_are_permission_denied():
    connection = memory_connection()
    payload = fixture_payload()
    payload["costs"] = {"error": {"status": 403, "body": {"error": {"code": "missing_scope"}}}}

    result = sync_openai_admin_usage_cost_payload(
        connection,
        payload,
        end_day_utc="2026-06-13",
        started_at="2026-06-14T00:00:00Z",
    )

    assert result.state.status == "ready"
    assert "partially available" in (result.state.message or "")
    assert result.usage_events_seen == 3
    assert result.cost_records_seen == 0
    assert query_rolling_7d_summary(connection, "2026-06-13").event_count == 109
    assert query_cost_total_usd(connection, "2026-06-12", "2026-06-13") is None


def test_openai_admin_sync_rejects_invalid_bucket_start_time():
    connection = memory_connection()
    payload = {
        "usage": {
            "data": [
                {
                    "start_time": 999999999999999999999999,
                    "results": [
                        {
                            "input_tokens": 10,
                            "output_tokens": 2,
                        }
                    ],
                }
            ]
        },
        "costs": {"data": []},
    }

    try:
        sync_openai_admin_usage_cost_payload(
            connection,
            payload,
            end_day_utc="2026-06-13",
            started_at="2026-06-14T00:00:00Z",
        )
    except ContractError as exc:
        assert "OpenAI Admin bucket start_time is invalid" in str(exc)
    else:
        raise AssertionError("expected invalid bucket start_time to fail")
