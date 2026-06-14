"""Explicit source discovery for aggregate JSONL adapters.

Discovery here is intentionally opt-in: callers must provide the roots to
inspect. Default user-home probing stays in experiments until it is safe enough
to graduate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from backend.core import ContractError
from backend.sources.base import SourceAdapter, SourceState
from backend.sources.jsonl_usage import ClaudeCodeJsonlAdapter, CodexJsonlAdapter


@dataclass(frozen=True)
class JsonlSourceCandidate:
    source_kind: str
    root: Path
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_id is not None and not self.source_id.strip():
            raise ContractError("source_id must not be blank")


@dataclass(frozen=True)
class DiscoveredJsonlSource:
    source_kind: str
    source_id: str
    root: Path
    state: SourceState
    adapter: SourceAdapter


def discover_jsonl_sources(
    candidates: Iterable[JsonlSourceCandidate],
) -> list[DiscoveredJsonlSource]:
    return [
        discover_jsonl_source(candidate)
        for candidate in candidates
    ]


def discover_jsonl_source(candidate: JsonlSourceCandidate) -> DiscoveredJsonlSource:
    adapter = jsonl_adapter_for_candidate(candidate)
    state = adapter.get_state()
    return DiscoveredJsonlSource(
        source_kind=state.source_kind,
        source_id=state.source_id,
        root=candidate.root,
        state=state,
        adapter=adapter,
    )


def jsonl_adapter_for_candidate(candidate: JsonlSourceCandidate) -> SourceAdapter:
    if candidate.source_kind == "codex":
        return CodexJsonlAdapter(
            root=candidate.root,
            source_id=candidate.source_id or "codex:local_jsonl",
        )
    if candidate.source_kind == "claude_code":
        return ClaudeCodeJsonlAdapter(
            root=candidate.root,
            source_id=candidate.source_id or "claude_code:local_jsonl",
        )
    raise ContractError(
        f"{candidate.source_kind} does not have a mature aggregate JSONL adapter"
    )
