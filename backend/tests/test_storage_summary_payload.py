import sqlite3
import json

from backend.core import UsageEvent
from backend.fixtures.storage_seed_summary import (
    build_storage_seed_summary_payload,
    seed_mock_storage,
    write_storage_seed_summary,
)
from backend.fixtures.mock_summary import (
    build_mock_summary_payload,
    mock_source_states,
)
from backend.storage import (
    CostBucketRecord,
    build_storage_summary_payload,
    initialize_schema,
    record_cost_records,
    record_usage_events,
    upsert_source,
)


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_storage_payload_matches_mock_summary_shape_from_seed_data():
    connection = memory_connection()
    seed_mock_storage(connection)

    payload = build_storage_summary_payload(
        connection,
        end_day_utc="2026-06-14",
        generated_from="backend.tests.seed",
    )
    expected = build_mock_summary_payload()

    assert payload["schema_version"] == 1
    assert payload["generated_from"] == "backend.tests.seed"
    assert payload["privacy"] == {
        "synthetic": False,
        "stores_prompt_content": False,
        "stores_response_content": False,
        "stores_tool_output": False,
    }
    assert payload["refresh_state"] == {
        "last_attempt_at": None,
        "last_success_at": None,
        "last_status": "never_refreshed",
        "successful_source_count": 0,
        "attempted_source_count": 0,
        "events_seen": 0,
    }
    assert payload["summary"] == expected["summary"]
    assert payload["cost_summary"] == expected["cost_summary"]
    assert payload["allowance_windows"] == expected["allowance_windows"]
    assert payload["source_states"] == expected["source_states"]


def test_storage_seed_fixture_builds_the_same_payload_shape():
    payload = build_storage_seed_summary_payload()
    expected = build_mock_summary_payload()

    assert payload["generated_from"] == "backend.fixtures.storage_seed_summary"
    assert payload["refresh_state"]["last_status"] == "never_refreshed"
    assert payload["summary"] == expected["summary"]
    assert payload["cost_summary"] == expected["cost_summary"]
    assert payload["allowance_windows"] == expected["allowance_windows"]
    assert payload["source_states"] == expected["source_states"]


def test_storage_seed_fixture_can_export_json(tmp_path):
    output_path = tmp_path / "storage-seed-summary.json"

    write_storage_seed_summary(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == build_storage_seed_summary_payload()


def test_storage_payload_uses_rolling_7d_window_not_all_time_data():
    connection = memory_connection()
    seed_mock_storage(connection)
    record_usage_events(
        connection,
        [
            UsageEvent(
                source_kind="codex",
                source_id="codex:mock",
                started_at="2026-06-07T12:00:00Z",
                input_tokens=90,
                output_tokens=10,
                total_tokens=100,
                confidence="local_exact",
            )
        ],
    )

    payload = build_storage_summary_payload(connection, end_day_utc="2026-06-14")

    assert payload["summary"]["event_count"] == 6
    assert payload["summary"]["totals"]["total_tokens"] == 60140
    assert payload["summary"]["rolling_7d"]["window_start"] == "2026-06-08"
    assert payload["summary"]["rolling_7d"]["window_end"] == "2026-06-14"
    assert "2026-06-07" not in payload["summary"]["by_day"]


def test_storage_payload_keeps_daily_source_split_separate_from_rolling_source_split():
    connection = memory_connection()
    seed_mock_storage(connection)
    record_usage_events(
        connection,
        [
            UsageEvent(
                source_kind="codex",
                source_id="codex:mock",
                started_at="2026-06-13T12:00:00Z",
                input_tokens=900,
                output_tokens=100,
                total_tokens=1000,
                confidence="local_exact",
            )
        ],
    )

    payload = build_storage_summary_payload(connection, end_day_utc="2026-06-14")

    assert payload["summary"]["by_source"]["codex"]["total_tokens"] == 3540
    assert payload["summary"]["by_day"]["2026-06-14"]["total_tokens"] == 60140
    assert payload["summary"]["by_day_source"]["2026-06-14"]["codex"]["total_tokens"] == 2540
    assert payload["summary"]["by_day_source"]["2026-06-13"]["codex"]["total_tokens"] == 1000


def test_storage_payload_preserves_unavailable_allowance_without_fake_remaining():
    connection = memory_connection()
    seed_mock_storage(connection)

    payload = build_storage_summary_payload(connection, end_day_utc="2026-06-14")
    unavailable = [
        window
        for window in payload["allowance_windows"]
        if window["status"] == "unavailable"
    ]

    assert unavailable
    for window in unavailable:
        assert "remaining_amount" not in window
        assert "limit_amount" not in window
        assert "reset_at" not in window


def test_storage_payload_reports_empty_cost_summary_explicitly():
    connection = memory_connection()

    payload = build_storage_summary_payload(connection, end_day_utc="2026-06-14")

    assert payload["cost_summary"] == {
        "window_start": "2026-06-08",
        "window_end": "2026-06-14",
        "total_usd": None,
        "by_source": {},
    }


def test_storage_payload_reports_cost_summary_without_raw_ids():
    connection = memory_connection()
    record_cost_records(
        connection,
        [
            CostBucketRecord(
                day_utc="2026-06-14",
                source_kind="openai_api_cost",
                source_id="openai_api_cost:admin_api",
                project_id="project_hash",
                api_key_id="key_hash",
                cost_usd=1.25,
                event_count=3,
            )
        ],
    )

    payload = build_storage_summary_payload(connection, end_day_utc="2026-06-14")
    text = json.dumps(payload, sort_keys=True)

    assert payload["cost_summary"] == {
        "window_start": "2026-06-08",
        "window_end": "2026-06-14",
        "total_usd": 1.25,
        "by_source": {
            "openai_api_cost": {
                "total_usd": 1.25,
                "bucket_count": 1,
                "event_count": 3,
            },
        },
    }
    assert "project_hash" not in text
    assert "key_hash" not in text
