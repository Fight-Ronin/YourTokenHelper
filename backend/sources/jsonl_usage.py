"""Aggregate-only JSONL source adapters for Codex and Claude Code fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core import ContractError, UsageEvent
from backend.sources.base import SourceState


@dataclass(frozen=True)
class CodexJsonlAdapter:
    root: Path
    source_kind: str = "codex"
    source_id: str = "codex:local_jsonl"

    def get_state(self) -> SourceState:
        return jsonl_source_state(
            source_kind=self.source_kind,
            source_id=self.source_id,
            root=self.root,
        )

    def read_events(self) -> list[UsageEvent]:
        return read_usage_jsonl_events(
            self.root,
            source_kind=self.source_kind,
            source_id=self.source_id,
            confidence="local_exact",
        )


@dataclass(frozen=True)
class ClaudeCodeJsonlAdapter:
    root: Path
    source_kind: str = "claude_code"
    source_id: str = "claude_code:local_jsonl"

    def get_state(self) -> SourceState:
        return jsonl_source_state(
            source_kind=self.source_kind,
            source_id=self.source_id,
            root=self.root,
        )

    def read_events(self) -> list[UsageEvent]:
        return read_usage_jsonl_events(
            self.root,
            source_kind=self.source_kind,
            source_id=self.source_id,
            confidence="local_exact",
        )


@dataclass(frozen=True)
class CursorJsonlAdapter:
    root: Path
    source_kind: str = "cursor"
    source_id: str = "cursor:usage_import"

    def get_state(self) -> SourceState:
        return jsonl_source_state(
            source_kind=self.source_kind,
            source_id=self.source_id,
            root=self.root,
        )

    def read_events(self) -> list[UsageEvent]:
        return read_usage_jsonl_events(
            self.root,
            source_kind=self.source_kind,
            source_id=self.source_id,
            confidence="local_estimated",
        )


@dataclass(frozen=True)
class GeminiCliTelemetryAdapter:
    root: Path
    source_kind: str = "gemini_cli"
    source_id: str = "gemini_cli:telemetry_import"

    def get_state(self) -> SourceState:
        return jsonl_source_state(
            source_kind=self.source_kind,
            source_id=self.source_id,
            root=self.root,
        )

    def read_events(self) -> list[UsageEvent]:
        return read_usage_jsonl_events(
            self.root,
            source_kind=self.source_kind,
            source_id=self.source_id,
            confidence="local_exact",
        )


@dataclass(frozen=True)
class GithubCopilotReportAdapter:
    root: Path
    source_kind: str = "github_copilot"
    source_id: str = "github_copilot:official_report"

    def get_state(self) -> SourceState:
        return jsonl_source_state(
            source_kind=self.source_kind,
            source_id=self.source_id,
            root=self.root,
        )

    def read_events(self) -> list[UsageEvent]:
        return read_usage_jsonl_events(
            self.root,
            source_kind=self.source_kind,
            source_id=self.source_id,
            confidence="official",
        )


def jsonl_source_state(*, source_kind: str, source_id: str, root: Path) -> SourceState:
    if not root.exists():
        return SourceState(
            source_kind=source_kind,
            source_id=source_id,
            status="not_found",
            confidence="unavailable",
            message="Source path was not found.",
        )
    if not candidate_jsonl_files(root):
        return SourceState(
            source_kind=source_kind,
            source_id=source_id,
            status="setup_required",
            confidence="unavailable",
            message="No aggregate JSONL usage files were found.",
        )
    return SourceState(
        source_kind=source_kind,
        source_id=source_id,
        status="ready",
        confidence=ready_confidence(source_kind),
        message="Aggregate JSONL usage files are available.",
    )


def ready_confidence(source_kind: str) -> str:
    if source_kind == "cursor":
        return "local_estimated"
    if source_kind == "github_copilot":
        return "official"
    return "local_exact"


def read_usage_jsonl_events(
    root: Path,
    *,
    source_kind: str,
    source_id: str,
    confidence: str,
) -> list[UsageEvent]:
    events: list[UsageEvent] = []
    for path in candidate_jsonl_files(root):
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    record = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ContractError(f"Invalid JSONL record in {path.name}:{line_number}") from exc
                event = usage_event_from_record(
                    record,
                    source_kind=source_kind,
                    source_id=source_id,
                    confidence=confidence,
                )
                if event is not None:
                    events.append(event)
    return events


def candidate_jsonl_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if is_usage_record_file(root) else []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and is_usage_record_file(path)
    )


def is_usage_record_file(path: Path) -> bool:
    return path.suffix.lower() in {".jsonl", ".ndjson"} or path.name == "telemetry.log"


def usage_event_from_record(
    record: Any,
    *,
    source_kind: str,
    source_id: str,
    confidence: str,
) -> UsageEvent | None:
    if not isinstance(record, dict):
        return None
    usage = usage_payload_from_record(record, source_kind=source_kind)
    if usage is None:
        return None
    timestamp = timestamp_from_record(record)
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None

    input_tokens = first_int_value(usage, "input_tokens", "prompt_tokens", "input_token_count")
    output_tokens = first_int_value(usage, "output_tokens", "completion_tokens", "output_token_count")
    total_tokens = first_int_value(usage, "total_tokens", "tokens_used", "total_token_count")
    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    if total_tokens <= 0:
        return None

    return UsageEvent(
        source_kind=source_kind,
        source_id=source_id,
        started_at=timestamp,
        model=model_from_record(record, source_kind=source_kind),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens(usage),
        reasoning_output_tokens=reasoning_output_tokens(usage),
        cost_usd=float_value(record.get("cost_usd")),
        usage_credits=float_value(record.get("usage_credits")),
        total_tokens=total_tokens,
        confidence=confidence,
    )


def usage_payload_from_record(record: dict[str, Any], *, source_kind: str) -> dict[str, Any] | None:
    usage = record.get("usage")
    if isinstance(usage, dict):
        return usage
    if source_kind == "gemini_cli":
        attributes = record.get("attributes")
        if isinstance(attributes, dict):
            return attributes
    if source_kind == "codex":
        info = dict_at_path(record, "payload", "info")
        if info is not None:
            last_usage = info.get("last_token_usage")
            if isinstance(last_usage, dict):
                return last_usage
            total_usage = info.get("total_token_usage")
            if isinstance(total_usage, dict):
                return total_usage
    if source_kind == "claude_code":
        message = record.get("message")
        if isinstance(message, dict):
            message_usage = message.get("usage")
            if isinstance(message_usage, dict):
                return message_usage
    return None


def timestamp_from_record(record: dict[str, Any]) -> Any:
    timestamp = record.get("timestamp") or record.get("started_at") or record.get("created_at")
    if timestamp is not None:
        return timestamp
    day = record.get("date")
    if isinstance(day, str) and len(day) == 10 and day[4] == "-" and day[7] == "-":
        return f"{day}T00:00:00Z"
    return None


def model_from_record(record: dict[str, Any], *, source_kind: str) -> str | None:
    direct = string_value(record.get("model"))
    if direct is not None:
        return direct
    message = record.get("message")
    if isinstance(message, dict):
        message_model = string_value(message.get("model"))
        if message_model is not None:
            return message_model
    payload = record.get("payload")
    if isinstance(payload, dict):
        payload_model = string_value(payload.get("model"))
        if payload_model is not None:
            return payload_model
    if source_kind == "gemini_cli":
        attributes = record.get("attributes")
        if isinstance(attributes, dict):
            attributes_model = string_value(attributes.get("model"))
            if attributes_model is not None:
                return attributes_model
    info = dict_at_path(record, "payload", "info")
    if info is not None:
        return string_value(info.get("model")) or string_value(info.get("model_slug"))
    return None


def dict_at_path(record: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, dict) else None


def cached_input_tokens(usage: dict[str, Any]) -> int | None:
    direct = int_value(usage.get("cached_input_tokens"))
    if direct is not None:
        return direct
    parts = [
        int_value(usage.get("cache_read_input_tokens")),
        int_value(usage.get("cache_creation_input_tokens")),
        int_value(usage.get("cached_content_token_count")),
    ]
    total = sum(item for item in parts if item is not None)
    return total if total else None


def reasoning_output_tokens(usage: dict[str, Any]) -> int | None:
    return first_int_value(
        usage,
        "reasoning_output_tokens",
        "thoughts_token_count",
    )


def first_int_value(record: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = int_value(record.get(key))
        if value is not None:
            return value
    return None


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def float_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def string_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
