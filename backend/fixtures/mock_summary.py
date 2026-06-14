"""Synthetic V1 summary payload for desktop mock UI work."""

from __future__ import annotations

from typing import Any

from backend.core import (
    AllowanceWindow,
    UsageEvent,
    aggregate_usage,
    allowance_window_to_dict,
    usage_summary_to_dict,
)


def build_mock_summary_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_from": "backend.fixtures.mock_summary",
        "privacy": {
            "synthetic": True,
            "stores_prompt_content": False,
            "stores_response_content": False,
            "stores_tool_output": False,
        },
        "summary": usage_summary_to_dict(aggregate_usage(mock_usage_events())),
        "allowance_windows": [
            allowance_window_to_dict(window)
            for window in mock_allowance_windows()
        ],
        "source_states": mock_source_states(),
    }


def mock_usage_events() -> list[UsageEvent]:
    return [
        UsageEvent(
            source_kind="codex",
            source_id="codex:mock",
            started_at="2026-06-14T02:00:00Z",
            model="gpt-5.5",
            input_tokens=2100,
            output_tokens=400,
            cached_input_tokens=550,
            reasoning_output_tokens=40,
            total_tokens=2540,
            confidence="local_exact",
        ),
        UsageEvent(
            source_kind="claude_code",
            source_id="claude_code:mock",
            started_at="2026-06-14T03:00:00Z",
            model="claude-sonnet-5",
            input_tokens=4100,
            output_tokens=930,
            cached_input_tokens=1050,
            total_tokens=5030,
            confidence="local_exact",
        ),
        UsageEvent(
            source_kind="cursor",
            source_id="cursor:mock",
            started_at="2026-06-14T04:00:00Z",
            model="unknown",
            input_tokens=3100,
            output_tokens=680,
            total_tokens=3780,
            confidence="local_estimated",
        ),
        UsageEvent(
            source_kind="gemini_cli",
            source_id="gemini_cli:mock",
            started_at="2026-06-14T05:00:00Z",
            model="gemini-3-pro",
            input_tokens=1800,
            output_tokens=360,
            cached_input_tokens=120,
            reasoning_output_tokens=90,
            total_tokens=2250,
            confidence="local_estimated",
        ),
        UsageEvent(
            source_kind="github_copilot",
            source_id="github_copilot:mock",
            started_at="2026-06-14T06:00:00Z",
            input_tokens=2800,
            output_tokens=640,
            cached_input_tokens=500,
            total_tokens=3440,
            confidence="official",
        ),
        UsageEvent(
            source_kind="openai_api_cost",
            source_id="openai_api_cost:mock",
            started_at="2026-06-14T07:00:00Z",
            input_tokens=35200,
            output_tokens=7900,
            cached_input_tokens=8900,
            total_tokens=43100,
            confidence="official",
            cost_usd=1.03,
        ),
    ]


def mock_allowance_windows() -> list[AllowanceWindow]:
    return [
        AllowanceWindow(
            source_kind="codex",
            source_id="codex:mock",
            status="manual",
            unit="tokens",
            used_amount=2540,
            remaining_amount=97460,
            reset_at="2026-06-21T00:00:00Z",
            note="Synthetic manual allowance for mock UI.",
        ),
        AllowanceWindow(
            source_kind="claude_code",
            source_id="claude_code:mock",
            status="derived",
            unit="credits",
            used_amount=5.03,
            remaining_amount=14.97,
            reset_at="2026-06-18T00:00:00Z",
            note="Synthetic derived allowance for mock UI.",
        ),
        AllowanceWindow(
            source_kind="cursor",
            source_id="cursor:mock",
            status="unavailable",
            unit="unknown",
            used_amount=3780,
            note="Cursor local allowance is not available in V1 mock data.",
        ),
        AllowanceWindow(
            source_kind="gemini_cli",
            source_id="gemini_cli:mock",
            status="unavailable",
            unit="unknown",
            used_amount=2250,
            note="Gemini CLI allowance requires source-specific setup or manual data.",
        ),
        AllowanceWindow(
            source_kind="github_copilot",
            source_id="github_copilot:mock",
            status="unavailable",
            unit="unknown",
            used_amount=3440,
            note="GitHub Copilot personal local allowance is not assumed.",
        ),
        AllowanceWindow(
            source_kind="openai_api_cost",
            source_id="openai_api_cost:mock",
            status="unavailable",
            unit="usd",
            used_amount=1.03,
            note="OpenAI API cost is secondary and may not expose allowance.",
        ),
        AllowanceWindow(
            source_kind="claude_api_cost",
            source_id="claude_api_cost:mock",
            status="unavailable",
            unit="usd",
            note="Claude API cost is secondary and requires verified billing export or API coverage.",
        ),
        AllowanceWindow(
            source_kind="gemini_api_cost",
            source_id="gemini_api_cost:mock",
            status="unavailable",
            unit="usd",
            note="Gemini API cost is secondary and requires verified billing export or API coverage.",
        ),
        AllowanceWindow(
            source_kind="deepseek_api_cost",
            source_id="deepseek_api_cost:mock",
            status="unavailable",
            unit="usd",
            note="DeepSeek API cost is secondary and requires verified billing export or API coverage.",
        ),
    ]


def mock_source_states() -> list[dict[str, Any]]:
    return [
        {"source_kind": "codex", "status": "ready", "confidence": "local_exact"},
        {"source_kind": "claude_code", "status": "ready", "confidence": "local_exact"},
        {"source_kind": "cursor", "status": "not_found", "confidence": "local_estimated"},
        {"source_kind": "gemini_cli", "status": "setup_required", "confidence": "local_estimated"},
        {"source_kind": "github_copilot", "status": "official_report", "confidence": "official"},
        {"source_kind": "openai_api_cost", "status": "secondary_source", "confidence": "official"},
        {"source_kind": "claude_api_cost", "status": "secondary_source", "confidence": "unavailable"},
        {"source_kind": "gemini_api_cost", "status": "secondary_source", "confidence": "unavailable"},
        {"source_kind": "deepseek_api_cost", "status": "secondary_source", "confidence": "unavailable"},
    ]
