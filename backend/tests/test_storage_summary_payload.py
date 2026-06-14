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
    build_storage_summary_payload,
    initialize_schema,
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
    assert payload["summary"] == expected["summary"]
    assert payload["allowance_windows"] == expected["allowance_windows"]
    assert payload["source_states"] == expected["source_states"]


def test_storage_seed_fixture_builds_the_same_payload_shape():
    payload = build_storage_seed_summary_payload()
    expected = build_mock_summary_payload()

    assert payload["generated_from"] == "backend.fixtures.storage_seed_summary"
    assert payload["summary"] == expected["summary"]
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
