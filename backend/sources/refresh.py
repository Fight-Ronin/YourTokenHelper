"""Manual refresh orchestration for source adapters."""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any, Iterable

from backend.core import ContractError
from backend.sources.base import SourceAdapter, SyncResult, sync_source_adapter
from backend.storage import build_storage_summary_payload


def refresh_source_adapters(
    connection: sqlite3.Connection,
    adapters: Iterable[SourceAdapter],
    *,
    end_day_utc: str | None = None,
    started_at: str | None = None,
) -> list[SyncResult]:
    replacement_window = rolling_7d_window_for_end_day(end_day_utc) if end_day_utc else None
    return [
        sync_source_adapter(
            connection,
            adapter,
            started_at=started_at,
            replace_start_day_utc=replacement_window[0] if replacement_window else None,
            replace_end_day_utc=replacement_window[1] if replacement_window else None,
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
        end_day_utc=end_day_utc,
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


def rolling_7d_window_for_end_day(end_day_utc: str) -> tuple[str, str]:
    try:
        end_day = dt.date.fromisoformat(end_day_utc)
    except ValueError as exc:
        raise ContractError("end_day_utc must be YYYY-MM-DD") from exc
    if end_day.isoformat() != end_day_utc:
        raise ContractError("end_day_utc must be YYYY-MM-DD")
    start_day = end_day - dt.timedelta(days=6)
    return start_day.isoformat(), end_day.isoformat()


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
