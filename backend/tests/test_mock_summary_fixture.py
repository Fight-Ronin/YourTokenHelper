import json
from pathlib import Path

from backend.fixtures.mock_summary import build_mock_summary_payload


FIXTURE_PATH = Path("backend/fixtures/mock_v1_summary.json")


def test_mock_summary_fixture_matches_generator():
    expected = json.dumps(build_mock_summary_payload(), indent=2, sort_keys=True) + "\n"

    assert FIXTURE_PATH.read_text(encoding="utf-8") == expected


def test_mock_summary_fixture_has_pr3_ready_contract_shape():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["privacy"] == {
        "synthetic": True,
        "stores_prompt_content": False,
        "stores_response_content": False,
        "stores_tool_output": False,
    }
    assert payload["summary"]["event_count"] == 6
    assert payload["summary"]["totals"]["total_tokens"] == 60140
    assert payload["summary"]["rolling_7d"]["window_start"] == "2026-06-08"
    assert payload["summary"]["rolling_7d"]["window_end"] == "2026-06-14"
    assert {source["source_kind"] for source in payload["source_states"]} == {
        "codex",
        "claude_code",
        "cursor",
        "gemini_cli",
        "github_copilot",
        "openai_api_cost",
        "claude_api_cost",
        "gemini_api_cost",
        "deepseek_api_cost",
    }


def test_unavailable_mock_allowances_do_not_include_fake_remaining_or_reset():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    unavailable_windows = [
        item
        for item in payload["allowance_windows"]
        if item["status"] == "unavailable"
    ]
    assert unavailable_windows
    for window in unavailable_windows:
        assert "remaining_amount" not in window
        assert "limit_amount" not in window
        assert "reset_at" not in window
