"""Manual refresh orchestration for source adapters."""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from backend.sources.base import SourceAdapter, SyncResult, sync_source_adapter
from backend.storage import build_storage_summary_payload


def refresh_source_adapters(
    connection: sqlite3.Connection,
    adapters: Iterable[SourceAdapter],
    *,
    started_at: str | None = None,
) -> list[SyncResult]:
    return [
        sync_source_adapter(
            connection,
            adapter,
            started_at=started_at,
        )
        for adapter in adapters
    ]


def refresh_sources_summary_payload(
    connection: sqlite3.Connection,
    adapters: Iterable[SourceAdapter],
    *,
    end_day_utc: str,
    started_at: str | None = None,
) -> dict[str, Any]:
    results = refresh_source_adapters(
        connection,
        adapters,
        started_at=started_at,
    )
    return {
        "refresh_results": refresh_results_to_payload(results),
        "storage_summary": build_storage_summary_payload(
            connection,
            end_day_utc=end_day_utc,
            generated_from="backend.sources.refresh",
        ),
    }


def refresh_results_to_payload(
    results: Iterable[SyncResult],
) -> list[dict[str, object]]:
    return [
        sync_result_to_payload(result)
        for result in results
    ]


def sync_result_to_payload(result: SyncResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_kind": result.state.source_kind,
        "source_id": result.state.source_id,
        "status": result.state.status,
        "confidence": result.state.confidence,
        "events_seen": result.events_seen,
        "sync_run_id": result.sync_run_id,
    }
    if result.state.message:
        payload["message"] = result.state.message
    return payload
