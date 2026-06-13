#!/usr/bin/env python3
"""Normalize synthetic local-source fixtures into usage events."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOURCE_KINDS = ("codex", "claude_code", "cursor", "gemini_cli", "github_copilot")
CONFIDENCE_VALUES = {"official", "local_exact", "local_estimated", "manual", "unavailable"}
JSON_SUFFIXES = {".json", ".jsonl", ".ndjson"}


@dataclass(frozen=True)
class UsageEvent:
    source_kind: str
    source_id: str
    started_at: str
    total_tokens: int
    confidence: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    cost_usd: float | None = None
    usage_credits: float | None = None
    session_id: str | None = None
    workspace_id: str | None = None
    raw_source_ref: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse fixture usage events for local coding-tool sources."
    )
    parser.add_argument(
        "--fixture-root",
        required=True,
        help="Synthetic fixture root. This parser intentionally does not scan real local logs yet.",
    )
    parser.add_argument(
        "--source",
        choices=("all",) + SOURCE_KINDS,
        default="all",
        help="Source to parse from the fixture root.",
    )
    parser.add_argument(
        "--output",
        help="Write redacted aggregate summary JSON to this path. Defaults to stdout.",
    )
    parser.add_argument(
        "--include-events",
        action="store_true",
        help="Include normalized fixture events in the output for contract review.",
    )
    parser.add_argument(
        "--max-json-lines-per-file",
        type=int,
        default=1000,
        help="Maximum JSONL records to inspect per fixture file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixture_root = Path(args.fixture_root)
    source_kinds = SOURCE_KINDS if args.source == "all" else (args.source,)

    source_results = []
    events: list[UsageEvent] = []
    for source_kind in source_kinds:
        result = parse_source(source_kind, fixture_root / source_kind, args.max_json_lines_per_file)
        source_results.append(result)
        events.extend(result["events"])

    report = build_report(source_results, events, args.include_events)
    write_report(report, args.output)


def parse_source(source_kind: str, root: Path, max_json_lines: int) -> dict[str, Any]:
    if not root.exists():
        return source_result(source_kind, "not-found", [])

    events: list[UsageEvent] = []
    for path in candidate_fixture_files(root):
        for index, record in read_records(path, max_json_lines):
            event = extract_event(source_kind, record, raw_source_ref(path, index))
            if event is not None:
                events.append(event)

    status = "ready" if events else "no-events"
    return source_result(source_kind, status, events)


def source_result(source_kind: str, status: str, events: list[UsageEvent]) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "status": status,
        "event_count": len(events),
        "events": events,
    }


def candidate_fixture_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if is_json_record_file(root) else []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and is_json_record_file(path)
    )


def read_records(path: Path, max_json_lines: int) -> list[tuple[int, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"} or path.name == "telemetry.log":
        records = []
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                if index > max_json_lines:
                    break
                line = line.strip()
                if line:
                    records.append((index, json.loads(line)))
        return records
    return [(1, json.loads(path.read_text(encoding="utf-8")))]


def is_json_record_file(path: Path) -> bool:
    return path.suffix.lower() in JSON_SUFFIXES or path.name == "telemetry.log"


def extract_event(source_kind: str, record: Any, source_ref: str) -> UsageEvent | None:
    if not isinstance(record, dict):
        return None

    usage = first_dict_at(
        record,
        (
            ("usage",),
            ("message", "usage"),
            ("response", "usage"),
            ("payload", "info", "last_token_usage"),
            ("payload", "info", "total_token_usage"),
            ("attributes",),
        ),
    )
    if usage is None and has_token_shape(record):
        usage = record
    if usage is None:
        return None

    started_at = first_string_at(
        record,
        (
            ("timestamp",),
            ("started_at",),
            ("created_at",),
            ("date",),
            ("message", "timestamp"),
            ("payload", "timestamp"),
        ),
    )
    if not started_at:
        return None
    normalized_started_at = normalize_timestamp(started_at)
    if normalized_started_at is None:
        return None

    input_tokens = first_int_at(
        usage,
        (("input_tokens",), ("prompt_tokens",), ("input_token_count",)),
    )
    output_tokens = first_int_at(
        usage,
        (("output_tokens",), ("completion_tokens",), ("output_token_count",)),
    )
    total_tokens = first_int_at(
        usage,
        (("total_tokens",), ("tokens_used",), ("total_token_count",)),
    )
    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    if total_tokens <= 0:
        return None

    return UsageEvent(
        source_kind=source_kind,
        source_id=f"{source_kind}:fixture",
        started_at=normalized_started_at,
        model=first_string_at(
            record,
            (
                ("model",),
                ("message", "model"),
                ("payload", "model"),
                ("attributes", "model"),
                ("workflowProgress", "model"),
            ),
        ),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens(usage),
        reasoning_output_tokens=reasoning_output_tokens(usage),
        cost_usd=first_float_at(record, (("cost_usd",), ("usage", "cost_usd"))),
        usage_credits=first_float_at(record, (("usage_credits",), ("usage", "usage_credits"))),
        total_tokens=total_tokens,
        confidence=confidence(record, source_kind),
        session_id=first_string_at(record, (("session_id",), ("sessionId",))),
        workspace_id=first_string_at(record, (("workspace_id",), ("workspaceId",))),
        raw_source_ref=source_ref,
    )


def first_dict_at(value: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> dict[str, Any] | None:
    for path in paths:
        item = value_at(value, path)
        if isinstance(item, dict):
            return item
    return None


def first_string_at(value: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> str | None:
    for path in paths:
        item = value_at(value, path)
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def first_int_at(value: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> int | None:
    for path in paths:
        item = value_at(value, path)
        converted = to_int(item)
        if converted is not None:
            return converted
    return None


def value_at(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    item: Any = value
    for segment in path:
        if not isinstance(item, dict) or segment not in item:
            return None
        item = item[segment]
    return item


def has_token_shape(value: dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "input_tokens",
            "output_tokens",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "tokens_used",
            "input_token_count",
            "output_token_count",
            "total_token_count",
        )
    )


def to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def first_float_at(value: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> float | None:
    for path in paths:
        item = value_at(value, path)
        converted = to_float(item)
        if converted is not None:
            return converted
    return None


def to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return float(text)
        except ValueError:
            return None
    return None


def cached_input_tokens(usage: dict[str, Any]) -> int | None:
    direct = first_int_at(usage, (("cached_input_tokens",),))
    if direct is not None:
        return direct

    parts = [
        first_int_at(usage, (("cache_read_input_tokens",),)),
        first_int_at(usage, (("cache_creation_input_tokens",),)),
        first_int_at(usage, (("cached_content_token_count",),)),
        first_int_at(usage, (("input_token_details", "cached_tokens"),)),
        first_int_at(usage, (("cache_creation", "ephemeral_1h_input_tokens"),)),
        first_int_at(usage, (("cache_creation", "ephemeral_5m_input_tokens"),)),
    ]
    total = sum(item for item in parts if item is not None)
    return total if total else None


def reasoning_output_tokens(usage: dict[str, Any]) -> int | None:
    return first_int_at(
        usage,
        (
            ("reasoning_output_tokens",),
            ("thoughts_token_count",),
            ("output_tokens_details", "reasoning_tokens"),
        ),
    )


def confidence(record: dict[str, Any], source_kind: str) -> str:
    explicit = first_string_at(record, (("confidence",),))
    if explicit in CONFIDENCE_VALUES:
        return explicit
    if source_kind == "github_copilot":
        return "official"
    return "local_exact"


def normalize_timestamp(value: str) -> str | None:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def raw_source_ref(path: Path, line_number: int) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
    return f"{digest}:{line_number}"


def build_report(
    source_results: list[dict[str, Any]],
    events: list[UsageEvent],
    include_events: bool,
) -> dict[str, Any]:
    sorted_events = sorted(events, key=lambda item: item.started_at)
    summary = aggregate_events(sorted_events)
    report: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "privacy": {
            "stores_prompt_content": False,
            "stores_response_content": False,
            "stores_tool_output": False,
            "fixture_only": True,
        },
        "sources": [
            {
                "source_kind": item["source_kind"],
                "status": item["status"],
                "event_count": item["event_count"],
            }
            for item in source_results
        ],
        "summary": summary,
    }
    if include_events:
        report["events"] = [compact_event(event) for event in sorted_events]
    return report


def aggregate_events(events: list[UsageEvent]) -> dict[str, Any]:
    source_totals: dict[str, dict[str, int]] = {}
    daily_totals: dict[str, dict[str, int]] = {}

    for event in events:
        add_event(source_totals.setdefault(event.source_kind, empty_totals()), event)
        add_event(daily_totals.setdefault(event.started_at[:10], empty_totals()), event)

    rolling_7d = empty_totals()
    window = rolling_window(events)
    if window is not None:
        start_day, end_day = window
        for event in events:
            event_day = event.started_at[:10]
            if start_day <= event_day <= end_day:
                add_event(rolling_7d, event)

    return {
        "event_count": len(events),
        "totals": total_totals(events),
        "by_source": source_totals,
        "by_day": daily_totals,
        "rolling_7d": {
            "window_start": window[0] if window else None,
            "window_end": window[1] if window else None,
            "totals": rolling_7d,
        },
    }


def rolling_window(events: list[UsageEvent]) -> tuple[str, str] | None:
    if not events:
        return None
    latest_day = max(dt.date.fromisoformat(event.started_at[:10]) for event in events)
    start_day = latest_day - dt.timedelta(days=6)
    return start_day.isoformat(), latest_day.isoformat()


def total_totals(events: list[UsageEvent]) -> dict[str, int]:
    totals = empty_totals()
    for event in events:
        add_event(totals, event)
    return totals


def empty_totals() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
    }


def add_event(totals: dict[str, int], event: UsageEvent) -> None:
    totals["input_tokens"] += event.input_tokens or 0
    totals["output_tokens"] += event.output_tokens or 0
    totals["cached_input_tokens"] += event.cached_input_tokens or 0
    totals["reasoning_output_tokens"] += event.reasoning_output_tokens or 0
    totals["total_tokens"] += event.total_tokens


def compact_event(event: UsageEvent) -> dict[str, Any]:
    return {key: value for key, value in asdict(event).items() if value is not None}


def write_report(report: dict[str, Any], output: str | None) -> None:
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
        print(f"Wrote usage event fixture summary to {path}")
    else:
        print(encoded)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
