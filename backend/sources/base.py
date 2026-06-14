"""Source adapter contracts for local aggregate sync."""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from backend.core import CONFIDENCE_VALUES, SOURCE_KINDS, ContractError, UsageEvent
from backend.storage import (
    record_sync_run,
    record_usage_events,
    replace_usage_events_for_source_window,
    upsert_source,
)


SOURCE_STATUSES = (
    "ready",
    "not_found",
    "permission_denied",
    "setup_required",
    "official_report",
    "manual_only",
    "secondary_source",
    "error",
)


@dataclass(frozen=True)
class SourceState:
    source_kind: str
    source_id: str
    status: str
    confidence: str
    message: str | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in SOURCE_KINDS:
            raise ContractError(f"Unknown source_kind: {self.source_kind}")
        if not self.source_id.strip():
            raise ContractError("source_id is required")
        if self.status not in SOURCE_STATUSES:
            raise ContractError(f"Unknown source status: {self.status}")
        if self.confidence not in CONFIDENCE_VALUES:
            raise ContractError(f"Unknown confidence: {self.confidence}")


@dataclass(frozen=True)
class SyncResult:
    state: SourceState
    events_seen: int
    sync_run_id: int


class SourceAdapter(Protocol):
    source_kind: str
    source_id: str

    def get_state(self) -> SourceState:
        ...

    def read_events(self) -> list[UsageEvent]:
        ...


def sync_source_adapter(
    connection: sqlite3.Connection,
    adapter: SourceAdapter,
    *,
    started_at: str | None = None,
    replace_start_day_utc: str | None = None,
    replace_end_day_utc: str | None = None,
) -> SyncResult:
    if (replace_start_day_utc is None) != (replace_end_day_utc is None):
        raise ContractError("replacement window requires both start and end days")

    state = adapter.get_state()
    upsert_source(
        connection,
        source_kind=state.source_kind,
        source_id=state.source_id,
        status=state.status,
        confidence=state.confidence,
    )

    events: list[UsageEvent] = []
    if state.status == "ready":
        try:
            events = adapter.read_events()
            if replace_start_day_utc is not None and replace_end_day_utc is not None:
                events = [
                    event
                    for event in events
                    if replace_start_day_utc <= event.day_utc <= replace_end_day_utc
                ]
                replace_usage_events_for_source_window(
                    connection,
                    source_kind=state.source_kind,
                    source_id=state.source_id,
                    start_day_utc=replace_start_day_utc,
                    end_day_utc=replace_end_day_utc,
                    events=events,
                )
            else:
                record_usage_events(connection, events)
        except PermissionError:
            state = SourceState(
                source_kind=state.source_kind,
                source_id=state.source_id,
                status="permission_denied",
                confidence="unavailable",
                message="Permission denied while reading source aggregate data.",
            )
            upsert_source(
                connection,
                source_kind=state.source_kind,
                source_id=state.source_id,
                status=state.status,
                confidence=state.confidence,
            )
        except (ContractError, OSError):
            state = SourceState(
                source_kind=state.source_kind,
                source_id=state.source_id,
                status="error",
                confidence="unavailable",
                message="Source sync failed before aggregate events were stored.",
            )
            upsert_source(
                connection,
                source_kind=state.source_kind,
                source_id=state.source_id,
                status=state.status,
                confidence=state.confidence,
            )
    sync_run_id = record_sync_run(
        connection,
        source_kind=state.source_kind,
        source_id=state.source_id,
        status=state.status,
        started_at=started_at or _utc_now(),
        finished_at=_utc_now(),
        events_seen=len(events),
        message=state.message,
    )
    return SyncResult(
        state=state,
        events_seen=len(events),
        sync_run_id=sync_run_id,
    )


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
