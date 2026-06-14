"""Plain JSON-ready shapes for backend contracts."""

from __future__ import annotations

from typing import Any

from backend.core.aggregation import RollingWindowSummary, UsageSummary
from backend.core.models import AllowanceWindow, TokenTotals


def token_totals_to_dict(totals: TokenTotals) -> dict[str, int]:
    return {
        "input_tokens": totals.input_tokens,
        "output_tokens": totals.output_tokens,
        "cached_input_tokens": totals.cached_input_tokens,
        "reasoning_output_tokens": totals.reasoning_output_tokens,
        "total_tokens": totals.total_tokens,
    }


def rolling_window_to_dict(window: RollingWindowSummary) -> dict[str, Any]:
    return {
        "window_start": window.window_start,
        "window_end": window.window_end,
        "totals": token_totals_to_dict(window.totals),
    }


def usage_summary_to_dict(summary: UsageSummary) -> dict[str, Any]:
    return {
        "event_count": summary.event_count,
        "totals": token_totals_to_dict(summary.totals),
        "by_source": {
            source_kind: token_totals_to_dict(totals)
            for source_kind, totals in sorted(summary.by_source.items())
        },
        "by_day": {
            day: token_totals_to_dict(totals)
            for day, totals in sorted(summary.by_day.items())
        },
        "by_day_source": {
            day: {
                source_kind: token_totals_to_dict(totals)
                for source_kind, totals in sorted(source_totals.items())
            }
            for day, source_totals in sorted(summary.by_day_source.items())
        },
        "rolling_7d": rolling_window_to_dict(summary.rolling_7d),
    }


def allowance_window_to_dict(window: AllowanceWindow) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_kind": window.source_kind,
        "source_id": window.source_id,
        "status": window.status,
        "unit": window.unit,
    }
    for field_name in (
        "window_start",
        "window_end",
        "reset_at",
        "limit_amount",
        "used_amount",
        "remaining_amount",
        "note",
    ):
        value = getattr(window, field_name)
        if value is not None:
            result[field_name] = value
    return result
