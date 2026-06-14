"""SQLite storage for aggregate usage data."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from backend.core.aggregation import RollingWindowSummary, UsageSummary, add_totals
from backend.core.models import (
    CONFIDENCE_VALUES,
    SOURCE_KINDS,
    AllowanceWindow,
    ContractError,
    TokenTotals,
    UsageEvent,
    normalize_utc_timestamp,
)


SCHEMA_VERSION = 1
BREAKDOWN_COLUMNS = {
    "api_key_id": "api_key_id",
    "model": "model",
    "project_id": "project_id",
    "source_kind": "source_kind",
}


def connect_database(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    initialize_schema(connection)
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    with connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                display_name TEXT,
                status TEXT NOT NULL DEFAULT 'observed',
                confidence TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (source_kind, source_id)
            );

            CREATE TABLE IF NOT EXISTS usage_buckets (
                day_utc TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                project_id TEXT NOT NULL DEFAULT '',
                api_key_id TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL,
                event_count INTEGER NOT NULL CHECK (event_count >= 0),
                input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
                output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
                cached_input_tokens INTEGER NOT NULL CHECK (cached_input_tokens >= 0),
                reasoning_output_tokens INTEGER NOT NULL CHECK (reasoning_output_tokens >= 0),
                total_tokens INTEGER NOT NULL CHECK (total_tokens >= 0),
                PRIMARY KEY (
                    day_utc,
                    source_kind,
                    source_id,
                    model,
                    project_id,
                    api_key_id,
                    confidence
                )
            );

            CREATE TABLE IF NOT EXISTS cost_buckets (
                day_utc TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                project_id TEXT NOT NULL DEFAULT '',
                api_key_id TEXT NOT NULL DEFAULT '',
                currency TEXT NOT NULL DEFAULT 'USD',
                event_count INTEGER NOT NULL CHECK (event_count >= 0),
                cost_usd REAL NOT NULL CHECK (cost_usd >= 0),
                PRIMARY KEY (
                    day_utc,
                    source_kind,
                    source_id,
                    model,
                    project_id,
                    api_key_id,
                    currency
                )
            );

            CREATE TABLE IF NOT EXISTS allowance_windows (
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                status TEXT NOT NULL,
                unit TEXT NOT NULL,
                window_start TEXT,
                window_end TEXT,
                reset_at TEXT,
                limit_amount REAL,
                used_amount REAL,
                remaining_amount REAL,
                note TEXT,
                PRIMARY KEY (source_kind, source_id),
                CHECK (
                    status != 'unavailable'
                    OR (limit_amount IS NULL AND remaining_amount IS NULL AND reset_at IS NULL)
                )
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                events_seen INTEGER NOT NULL DEFAULT 0 CHECK (events_seen >= 0),
                message TEXT
            );
            """
        )


def upsert_source(
    connection: sqlite3.Connection,
    *,
    source_kind: str,
    source_id: str,
    confidence: str,
    status: str = "observed",
    display_name: str | None = None,
    is_enabled: bool = True,
) -> None:
    _validate_source(source_kind, source_id, confidence)
    with connection:
        _write_source(
            connection,
            source_kind=source_kind,
            source_id=source_id,
            confidence=confidence,
            status=status,
            display_name=display_name,
            is_enabled=is_enabled,
            preserve_existing_settings=False,
        )


def list_sources(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT source_kind, source_id, display_name, status, confidence, is_enabled
        FROM sources
        ORDER BY source_kind, source_id
        """
    ).fetchall()
    return [
        {
            "source_kind": row["source_kind"],
            "source_id": row["source_id"],
            "display_name": row["display_name"],
            "status": row["status"],
            "confidence": row["confidence"],
            "is_enabled": bool(row["is_enabled"]),
        }
        for row in rows
    ]


def record_usage_events(connection: sqlite3.Connection, events: Iterable[UsageEvent]) -> None:
    with connection:
        for event in events:
            _record_usage_event(connection, event)


def replace_usage_events_for_source_window(
    connection: sqlite3.Connection,
    *,
    source_kind: str,
    source_id: str,
    start_day_utc: str,
    end_day_utc: str,
    events: Iterable[UsageEvent],
) -> None:
    _validate_source(source_kind, source_id, "manual")
    start_day, end_day = _validate_day_range(start_day_utc, end_day_utc)
    event_list = list(events)
    for event in event_list:
        if event.source_kind != source_kind or event.source_id != source_id:
            raise ContractError("replacement events must match the source")

    with connection:
        connection.execute(
            """
            DELETE FROM usage_buckets
            WHERE source_kind = ? AND source_id = ? AND day_utc BETWEEN ? AND ?
            """,
            (source_kind, source_id, start_day, end_day),
        )
        connection.execute(
            """
            DELETE FROM cost_buckets
            WHERE source_kind = ? AND source_id = ? AND day_utc BETWEEN ? AND ?
            """,
            (source_kind, source_id, start_day, end_day),
        )
        for event in event_list:
            _record_usage_event(connection, event)


def replace_allowance_windows(
    connection: sqlite3.Connection,
    windows: Iterable[AllowanceWindow],
) -> None:
    with connection:
        connection.execute("DELETE FROM allowance_windows")
        for window in windows:
            connection.execute(
                """
                INSERT INTO allowance_windows (
                    source_kind,
                    source_id,
                    status,
                    unit,
                    window_start,
                    window_end,
                    reset_at,
                    limit_amount,
                    used_amount,
                    remaining_amount,
                    note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    window.source_kind,
                    window.source_id,
                    window.status,
                    window.unit,
                    window.window_start,
                    window.window_end,
                    window.reset_at,
                    window.limit_amount,
                    window.used_amount,
                    window.remaining_amount,
                    window.note,
                ),
            )


def query_allowance_windows(connection: sqlite3.Connection) -> list[AllowanceWindow]:
    rows = connection.execute(
        """
        SELECT *
        FROM allowance_windows
        ORDER BY source_kind, source_id
        """
    ).fetchall()
    return [
        AllowanceWindow(
            source_kind=row["source_kind"],
            source_id=row["source_id"],
            status=row["status"],
            unit=row["unit"],
            window_start=row["window_start"],
            window_end=row["window_end"],
            reset_at=row["reset_at"],
            limit_amount=row["limit_amount"],
            used_amount=row["used_amount"],
            remaining_amount=row["remaining_amount"],
            note=row["note"],
        )
        for row in rows
    ]


def query_daily_summary(connection: sqlite3.Connection, day_utc: str) -> UsageSummary:
    day = _validate_day(day_utc)
    return _query_usage_summary(connection, day, day)


def query_rolling_7d_summary(connection: sqlite3.Connection, end_day_utc: str) -> UsageSummary:
    end_day = _validate_day(end_day_utc)
    start_day = (dt.date.fromisoformat(end_day) - dt.timedelta(days=6)).isoformat()
    return _query_usage_summary(connection, start_day, end_day)


def query_daily_trend(
    connection: sqlite3.Connection,
    end_day_utc: str,
    *,
    days: int = 7,
) -> dict[str, TokenTotals]:
    if days <= 0:
        raise ContractError("days must be positive")
    end_day = dt.date.fromisoformat(_validate_day(end_day_utc))
    start_day = end_day - dt.timedelta(days=days - 1)
    summary = _query_usage_summary(connection, start_day.isoformat(), end_day.isoformat())
    return {
        (start_day + dt.timedelta(days=offset)).isoformat(): summary.by_day.get(
            (start_day + dt.timedelta(days=offset)).isoformat(),
            TokenTotals(),
        )
        for offset in range(days)
    }


def query_usage_breakdown(
    connection: sqlite3.Connection,
    start_day_utc: str,
    end_day_utc: str,
    *,
    dimension: str,
) -> dict[str, TokenTotals]:
    start_day, end_day = _validate_day_range(start_day_utc, end_day_utc)
    column = BREAKDOWN_COLUMNS.get(dimension)
    if column is None:
        raise ContractError(f"Unsupported breakdown dimension: {dimension}")

    rows = connection.execute(
        f"""
        SELECT
            {column} AS label,
            SUM(input_tokens) AS input_tokens,
            SUM(output_tokens) AS output_tokens,
            SUM(cached_input_tokens) AS cached_input_tokens,
            SUM(reasoning_output_tokens) AS reasoning_output_tokens,
            SUM(total_tokens) AS total_tokens
        FROM usage_buckets
        WHERE day_utc BETWEEN ? AND ?
        GROUP BY {column}
        ORDER BY total_tokens DESC
        """,
        (start_day, end_day),
    ).fetchall()
    return {
        row["label"] or "unknown": _totals_from_row(row)
        for row in rows
    }


def query_cost_total_usd(
    connection: sqlite3.Connection,
    start_day_utc: str,
    end_day_utc: str,
) -> float | None:
    start_day, end_day = _validate_day_range(start_day_utc, end_day_utc)
    row = connection.execute(
        """
        SELECT COUNT(*) AS bucket_count, SUM(cost_usd) AS cost_usd
        FROM cost_buckets
        WHERE day_utc BETWEEN ? AND ?
        """,
        (start_day, end_day),
    ).fetchone()
    if row["bucket_count"] == 0:
        return None
    return float(row["cost_usd"])


def record_sync_run(
    connection: sqlite3.Connection,
    *,
    source_kind: str,
    source_id: str,
    status: str,
    started_at: str,
    finished_at: str | None = None,
    events_seen: int = 0,
    message: str | None = None,
) -> int:
    _validate_source(source_kind, source_id, "manual")
    if events_seen < 0:
        raise ContractError("events_seen must be non-negative")
    started = normalize_utc_timestamp(started_at)
    finished = normalize_utc_timestamp(finished_at) if finished_at else None
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO sync_runs (
                source_kind,
                source_id,
                status,
                started_at,
                finished_at,
                events_seen,
                message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_kind, source_id, status, started, finished, events_seen, message),
        )
    return int(cursor.lastrowid)


def clear_aggregate_cache(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute("DELETE FROM usage_buckets")
        connection.execute("DELETE FROM cost_buckets")
        connection.execute("DELETE FROM allowance_windows")
        connection.execute("DELETE FROM sync_runs")


def _record_usage_event(connection: sqlite3.Connection, event: UsageEvent) -> None:
    _write_source(
        connection,
        source_kind=event.source_kind,
        source_id=event.source_id,
        confidence=event.confidence,
        status="observed",
        display_name=None,
        is_enabled=True,
        preserve_existing_settings=True,
    )
    totals = event.token_totals()
    bucket_values = (
        event.day_utc,
        event.source_kind,
        event.source_id,
        _bucket_text(event.model),
        _bucket_text(event.project_id),
        _bucket_text(event.api_key_id),
        event.confidence,
        1,
        totals.input_tokens,
        totals.output_tokens,
        totals.cached_input_tokens,
        totals.reasoning_output_tokens,
        totals.total_tokens,
    )
    connection.execute(
        """
        INSERT INTO usage_buckets (
            day_utc,
            source_kind,
            source_id,
            model,
            project_id,
            api_key_id,
            confidence,
            event_count,
            input_tokens,
            output_tokens,
            cached_input_tokens,
            reasoning_output_tokens,
            total_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(
            day_utc,
            source_kind,
            source_id,
            model,
            project_id,
            api_key_id,
            confidence
        ) DO UPDATE SET
            event_count = usage_buckets.event_count + excluded.event_count,
            input_tokens = usage_buckets.input_tokens + excluded.input_tokens,
            output_tokens = usage_buckets.output_tokens + excluded.output_tokens,
            cached_input_tokens = usage_buckets.cached_input_tokens + excluded.cached_input_tokens,
            reasoning_output_tokens = usage_buckets.reasoning_output_tokens + excluded.reasoning_output_tokens,
            total_tokens = usage_buckets.total_tokens + excluded.total_tokens
        """,
        bucket_values,
    )
    if event.cost_usd is not None:
        connection.execute(
            """
            INSERT INTO cost_buckets (
                day_utc,
                source_kind,
                source_id,
                model,
                project_id,
                api_key_id,
                currency,
                event_count,
                cost_usd
            )
            VALUES (?, ?, ?, ?, ?, ?, 'USD', 1, ?)
            ON CONFLICT(
                day_utc,
                source_kind,
                source_id,
                model,
                project_id,
                api_key_id,
                currency
            ) DO UPDATE SET
                event_count = cost_buckets.event_count + excluded.event_count,
                cost_usd = cost_buckets.cost_usd + excluded.cost_usd
            """,
            (
                event.day_utc,
                event.source_kind,
                event.source_id,
                _bucket_text(event.model),
                _bucket_text(event.project_id),
                _bucket_text(event.api_key_id),
                event.cost_usd,
            ),
        )


def _query_usage_summary(
    connection: sqlite3.Connection,
    start_day_utc: str,
    end_day_utc: str,
) -> UsageSummary:
    start_day, end_day = _validate_day_range(start_day_utc, end_day_utc)
    rows = connection.execute(
        """
        SELECT
            day_utc,
            source_kind,
            SUM(event_count) AS event_count,
            SUM(input_tokens) AS input_tokens,
            SUM(output_tokens) AS output_tokens,
            SUM(cached_input_tokens) AS cached_input_tokens,
            SUM(reasoning_output_tokens) AS reasoning_output_tokens,
            SUM(total_tokens) AS total_tokens
        FROM usage_buckets
        WHERE day_utc BETWEEN ? AND ?
        GROUP BY day_utc, source_kind
        ORDER BY day_utc, source_kind
        """,
        (start_day, end_day),
    ).fetchall()

    event_count = 0
    totals = TokenTotals()
    by_source: dict[str, TokenTotals] = {}
    by_day: dict[str, TokenTotals] = {}
    by_day_source: dict[str, dict[str, TokenTotals]] = {}
    for row in rows:
        row_totals = _totals_from_row(row)
        event_count += int(row["event_count"])
        totals = add_totals(totals, row_totals)
        by_source[row["source_kind"]] = add_totals(
            by_source.get(row["source_kind"], TokenTotals()),
            row_totals,
        )
        by_day[row["day_utc"]] = add_totals(
            by_day.get(row["day_utc"], TokenTotals()),
            row_totals,
        )
        day_sources = by_day_source.setdefault(row["day_utc"], {})
        day_sources[row["source_kind"]] = add_totals(
            day_sources.get(row["source_kind"], TokenTotals()),
            row_totals,
        )

    return UsageSummary(
        event_count=event_count,
        totals=totals,
        by_source=by_source,
        by_day=by_day,
        by_day_source=by_day_source,
        rolling_7d=RollingWindowSummary(
            window_start=start_day if event_count else None,
            window_end=end_day if event_count else None,
            totals=totals,
        ),
    )


def _totals_from_row(row: sqlite3.Row) -> TokenTotals:
    return TokenTotals(
        input_tokens=int(row["input_tokens"] or 0),
        output_tokens=int(row["output_tokens"] or 0),
        cached_input_tokens=int(row["cached_input_tokens"] or 0),
        reasoning_output_tokens=int(row["reasoning_output_tokens"] or 0),
        total_tokens=int(row["total_tokens"] or 0),
    )


def _write_source(
    connection: sqlite3.Connection,
    *,
    source_kind: str,
    source_id: str,
    confidence: str,
    status: str,
    display_name: str | None,
    is_enabled: bool,
    preserve_existing_settings: bool,
) -> None:
    now = _utc_now()
    update_clause = (
        """
        confidence = excluded.confidence,
        updated_at = excluded.updated_at
        """
        if preserve_existing_settings
        else
        """
        display_name = excluded.display_name,
        status = excluded.status,
        confidence = excluded.confidence,
        is_enabled = excluded.is_enabled,
        updated_at = excluded.updated_at
        """
    )
    connection.execute(
        f"""
        INSERT INTO sources (
            source_kind,
            source_id,
            display_name,
            status,
            confidence,
            is_enabled,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_kind, source_id) DO UPDATE SET
            {update_clause}
        """,
        (
            source_kind,
            source_id,
            display_name,
            status,
            confidence,
            1 if is_enabled else 0,
            now,
            now,
        ),
    )


def _validate_source(source_kind: str, source_id: str, confidence: str) -> None:
    if source_kind not in SOURCE_KINDS:
        raise ContractError(f"Unknown source_kind: {source_kind}")
    if not source_id.strip():
        raise ContractError("source_id is required")
    if confidence not in CONFIDENCE_VALUES:
        raise ContractError(f"Unknown confidence: {confidence}")


def _validate_day_range(start_day_utc: str, end_day_utc: str) -> tuple[str, str]:
    start_day = _validate_day(start_day_utc)
    end_day = _validate_day(end_day_utc)
    if start_day > end_day:
        raise ContractError("start_day_utc must be on or before end_day_utc")
    return start_day, end_day


def _validate_day(day_utc: str) -> str:
    try:
        parsed = dt.date.fromisoformat(day_utc)
    except ValueError as exc:
        raise ContractError(f"day must be YYYY-MM-DD: {day_utc}") from exc
    return parsed.isoformat()


def _bucket_text(value: str | None) -> str:
    return value.strip() if value else ""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
