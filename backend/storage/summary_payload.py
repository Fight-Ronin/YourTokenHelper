"""Build UI-ready summary payloads from local aggregate storage."""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.core import SOURCE_KINDS, allowance_window_to_dict, usage_summary_to_dict
from backend.storage.sqlite_store import (
    list_sources,
    query_allowance_windows,
    query_rolling_7d_summary,
)


def build_storage_summary_payload(
    connection: sqlite3.Connection,
    *,
    end_day_utc: str,
    generated_from: str = "backend.storage.summary_payload",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_from": generated_from,
        "privacy": {
            "synthetic": False,
            "stores_prompt_content": False,
            "stores_response_content": False,
            "stores_tool_output": False,
        },
        "summary": usage_summary_to_dict(
            query_rolling_7d_summary(connection, end_day_utc)
        ),
        "allowance_windows": allowance_windows_to_payload(
            query_allowance_windows(connection)
        ),
        "source_states": source_states_to_payload(list_sources(connection)),
    }


def allowance_windows_to_payload(windows: list[Any]) -> list[dict[str, Any]]:
    source_rank = source_kind_rank()
    return [
        allowance_window_to_dict(window)
        for window in sorted(
            windows,
            key=lambda item: (
                source_rank.get(item.source_kind, len(SOURCE_KINDS)),
                item.source_id,
            ),
        )
    ]


def source_states_to_payload(sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    source_rank = source_kind_rank()
    return [
        {
            "source_kind": source["source_kind"],
            "status": source["status"],
            "confidence": source["confidence"],
        }
        for source in sorted(
            sources,
            key=lambda item: (
                source_rank.get(item["source_kind"], len(SOURCE_KINDS)),
                item["source_id"],
            ),
        )
    ]


def source_kind_rank() -> dict[str, int]:
    return {
        source_kind: index
        for index, source_kind in enumerate(SOURCE_KINDS)
    }
