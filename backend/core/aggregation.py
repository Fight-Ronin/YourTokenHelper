"""Aggregate normalized usage events for Daily and rolling Weekly views."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

from backend.core.models import TokenTotals, UsageEvent


@dataclass(frozen=True)
class RollingWindowSummary:
    window_start: str | None
    window_end: str | None
    totals: TokenTotals


@dataclass(frozen=True)
class UsageSummary:
    event_count: int
    totals: TokenTotals
    by_source: dict[str, TokenTotals]
    by_day: dict[str, TokenTotals]
    rolling_7d: RollingWindowSummary


def aggregate_usage(events: Iterable[UsageEvent]) -> UsageSummary:
    sorted_events = sorted(events, key=lambda event: event.started_at)
    by_source: dict[str, TokenTotals] = {}
    by_day: dict[str, TokenTotals] = {}

    for event in sorted_events:
        by_source[event.source_kind] = add_totals(
            by_source.get(event.source_kind, TokenTotals()),
            event.token_totals(),
        )
        by_day[event.day_utc] = add_totals(
            by_day.get(event.day_utc, TokenTotals()),
            event.token_totals(),
        )

    window_start, window_end = rolling_window(sorted_events)
    rolling_totals = TokenTotals()
    if window_start and window_end:
        for event in sorted_events:
            if window_start <= event.day_utc <= window_end:
                rolling_totals = add_totals(rolling_totals, event.token_totals())

    return UsageSummary(
        event_count=len(sorted_events),
        totals=sum_totals(event.token_totals() for event in sorted_events),
        by_source=by_source,
        by_day=by_day,
        rolling_7d=RollingWindowSummary(
            window_start=window_start,
            window_end=window_end,
            totals=rolling_totals,
        ),
    )


def rolling_window(events: list[UsageEvent]) -> tuple[str | None, str | None]:
    if not events:
        return None, None
    latest_day = max(dt.date.fromisoformat(event.day_utc) for event in events)
    start_day = latest_day - dt.timedelta(days=6)
    return start_day.isoformat(), latest_day.isoformat()


def sum_totals(totals: Iterable[TokenTotals]) -> TokenTotals:
    result = TokenTotals()
    for item in totals:
        result = add_totals(result, item)
    return result


def add_totals(left: TokenTotals, right: TokenTotals) -> TokenTotals:
    return TokenTotals(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        cached_input_tokens=left.cached_input_tokens + right.cached_input_tokens,
        reasoning_output_tokens=left.reasoning_output_tokens + right.reasoning_output_tokens,
        total_tokens=left.total_tokens + right.total_tokens,
    )
