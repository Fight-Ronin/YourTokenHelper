"""Deterministic source adapters used before live local parsers are connected."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core import UsageEvent
from backend.fixtures.mock_summary import mock_usage_events
from backend.sources.base import SourceState


@dataclass(frozen=True)
class CodexFixtureAdapter:
    source_kind: str = "codex"
    source_id: str = "codex:mock"

    def get_state(self) -> SourceState:
        return SourceState(
            source_kind=self.source_kind,
            source_id=self.source_id,
            status="ready",
            confidence="local_exact",
            message="Synthetic Codex adapter; live local parser is not connected yet.",
        )

    def read_events(self) -> list[UsageEvent]:
        return _events_for_source(self.source_kind)


@dataclass(frozen=True)
class ClaudeCodeFixtureAdapter:
    source_kind: str = "claude_code"
    source_id: str = "claude_code:mock"

    def get_state(self) -> SourceState:
        return SourceState(
            source_kind=self.source_kind,
            source_id=self.source_id,
            status="ready",
            confidence="local_exact",
            message="Synthetic Claude Code adapter; live local parser is not connected yet.",
        )

    def read_events(self) -> list[UsageEvent]:
        return _events_for_source(self.source_kind)


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


def _events_for_source(source_kind: str) -> list[UsageEvent]:
    return [
        event
        for event in mock_usage_events()
        if event.source_kind == source_kind
    ]
