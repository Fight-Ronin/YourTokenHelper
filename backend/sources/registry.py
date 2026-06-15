"""Build source setup adapters for the primary local coding tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.core import ContractError, UsageEvent
from backend.sources.base import SourceAdapter, SourceState
from backend.sources.discovery import JsonlSourceCandidate, discover_jsonl_sources


PRIMARY_LOCAL_SOURCE_KINDS = (
    "codex",
    "claude_code",
    "cursor",
    "gemini_cli",
    "github_copilot",
)


@dataclass(frozen=True)
class ManualStatusAdapter:
    source_kind: str
    source_id: str
    status: str
    confidence: str
    message: str | None = None

    def get_state(self) -> SourceState:
        return SourceState(
            source_kind=self.source_kind,
            source_id=self.source_id,
            status=self.status,
            confidence=self.confidence,
            message=self.message,
        )

    def read_events(self) -> list[UsageEvent]:
        return []


def build_primary_source_adapters(
    jsonl_candidates: Iterable[JsonlSourceCandidate] = (),
) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = []
    configured_kinds: set[str] = set()

    for discovered in discover_jsonl_sources(jsonl_candidates):
        adapters.append(discovered.adapter)
        configured_kinds.add(discovered.source_kind)

    for source_kind in PRIMARY_LOCAL_SOURCE_KINDS:
        if source_kind not in configured_kinds:
            adapters.append(setup_status_adapter(source_kind))

    return adapters


def setup_status_adapter(source_kind: str) -> ManualStatusAdapter:
    if source_kind == "codex":
        return ManualStatusAdapter(
            source_kind="codex",
            source_id="codex:setup",
            status="setup_required",
            confidence="unavailable",
            message="Choose an explicit Codex aggregate JSONL root before sync.",
        )
    if source_kind == "claude_code":
        return ManualStatusAdapter(
            source_kind="claude_code",
            source_id="claude_code:setup",
            status="setup_required",
            confidence="unavailable",
            message="Choose an explicit Claude Code aggregate JSONL root before sync.",
        )
    if source_kind == "cursor":
        return ManualStatusAdapter(
            source_kind="cursor",
            source_id="cursor:manual",
            status="manual_only",
            confidence="manual",
            message="Cursor supports explicit usage export import; choose a report root when available.",
        )
    if source_kind == "gemini_cli":
        return ManualStatusAdapter(
            source_kind="gemini_cli",
            source_id="gemini_cli:setup",
            status="setup_required",
            confidence="unavailable",
            message="Gemini CLI supports explicit telemetry import after telemetry/export setup.",
        )
    if source_kind == "github_copilot":
        return ManualStatusAdapter(
            source_kind="github_copilot",
            source_id="github_copilot:official_report",
            status="official_report",
            confidence="official",
            message="GitHub Copilot supports official usage metrics report import.",
        )
    raise ContractError(f"Unsupported primary source setup kind: {source_kind}")
