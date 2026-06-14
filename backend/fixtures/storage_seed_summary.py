"""SQLite-seeded synthetic V1 summary payload."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Sequence

from backend.fixtures.mock_summary import (
    mock_allowance_windows,
    mock_source_states,
    mock_usage_events,
)
from backend.storage import (
    build_storage_summary_payload,
    initialize_schema,
    record_usage_events,
    replace_allowance_windows,
    upsert_source,
)


DEFAULT_END_DAY_UTC = "2026-06-14"
GENERATED_FROM = "backend.fixtures.storage_seed_summary"


def build_storage_seed_summary_payload(
    *,
    end_day_utc: str = DEFAULT_END_DAY_UTC,
) -> dict:
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    seed_mock_storage(connection)
    return build_storage_summary_payload(
        connection,
        end_day_utc=end_day_utc,
        generated_from=GENERATED_FROM,
    )


def seed_mock_storage(connection: sqlite3.Connection) -> None:
    for source in mock_source_states():
        upsert_source(
            connection,
            source_kind=source["source_kind"],
            source_id=f"{source['source_kind']}:mock",
            confidence=source["confidence"],
            status=source["status"],
        )
    record_usage_events(connection, mock_usage_events())
    replace_allowance_windows(connection, mock_allowance_windows())


def write_storage_seed_summary(
    output_path: Path,
    *,
    end_day_utc: str = DEFAULT_END_DAY_UTC,
) -> None:
    payload = build_storage_seed_summary_payload(end_day_utc=end_day_utc)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the synthetic SQLite-seeded V1 summary payload.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path for the generated JSON payload.",
    )
    parser.add_argument(
        "--end-day-utc",
        default=DEFAULT_END_DAY_UTC,
        help="Inclusive rolling 7-day end day in YYYY-MM-DD format.",
    )
    args = parser.parse_args(argv)

    write_storage_seed_summary(args.output, end_day_utc=args.end_day_utc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
