import json
from pathlib import Path

from backend.fixtures.source_refresh_summary import (
    build_source_refresh_error_payload,
    build_source_refresh_summary_payload,
    write_source_refresh_error,
    write_source_refresh_summary,
)

DESKTOP_SAMPLE_PATH = Path("apps/desktop/src-tauri/source-refresh-summary.sample.json")
DESKTOP_ERROR_SAMPLE_PATH = Path(
    "apps/desktop/src-tauri/source-refresh-error.sample.json"
)


def test_source_refresh_summary_fixture_builds_pr5_handoff_payload():
    payload = build_source_refresh_summary_payload()

    assert list(payload) == ["refresh_results", "storage_summary"]
    assert [item["source_kind"] for item in payload["refresh_results"]] == [
        "codex",
        "claude_code",
        "cursor",
        "gemini_cli",
        "github_copilot",
    ]
    assert [item["events_seen"] for item in payload["refresh_results"]] == [2, 2, 1, 1, 1]
    assert payload["storage_summary"]["generated_from"] == "backend.sources.refresh"
    assert payload["storage_summary"]["refresh_state"] == {
        "last_attempt_at": "2026-06-14T00:00:00Z",
        "last_success_at": "2026-06-14T00:00:00Z",
        "last_status": "succeeded",
        "successful_source_count": 5,
        "attempted_source_count": 5,
        "events_seen": 7,
    }
    assert payload["storage_summary"]["summary"]["event_count"] == 7
    assert payload["storage_summary"]["summary"]["totals"]["total_tokens"] == 17040
    assert payload["storage_summary"]["cost_summary"] == {
        "window_start": "2026-06-08",
        "window_end": "2026-06-14",
        "total_usd": None,
        "by_source": {},
    }


def test_source_refresh_summary_fixture_can_export_json(tmp_path):
    output_path = tmp_path / "source-refresh-summary.json"

    write_source_refresh_summary(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == build_source_refresh_summary_payload()


def test_source_refresh_error_fixture_can_export_json(tmp_path):
    output_path = tmp_path / "source-refresh-error.json"

    write_source_refresh_error(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == build_source_refresh_error_payload()


def test_source_refresh_summary_desktop_sample_matches_backend_fixture():
    payload = json.loads(DESKTOP_SAMPLE_PATH.read_text(encoding="utf-8"))

    assert payload == build_source_refresh_summary_payload()


def test_source_refresh_error_desktop_sample_matches_backend_fixture():
    payload = json.loads(DESKTOP_ERROR_SAMPLE_PATH.read_text(encoding="utf-8"))

    assert payload == build_source_refresh_error_payload()


def test_source_refresh_summary_fixture_does_not_export_source_paths():
    payload = build_source_refresh_summary_payload()
    text = json.dumps(payload, sort_keys=True)

    assert "experiments/fixtures" not in text
    assert "local_sources" not in text
    assert "sessions" not in text
    assert "projects" not in text
    for item in payload["refresh_results"]:
        assert "root" not in item
        assert "path" not in item
        assert "file" not in item


def test_source_refresh_error_fixture_does_not_export_source_paths():
    payload = build_source_refresh_error_payload()
    text = json.dumps(payload, sort_keys=True)

    assert "C:/Users" not in text
    assert "secret" not in text
    assert "source_root" not in text
    assert "source_path" not in text
