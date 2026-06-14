"""Synthetic PR5 source refresh-summary payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from backend.sources import (
    build_primary_refresh_command_payload,
    build_primary_refresh_command_response_from_mapping,
)


DEFAULT_END_DAY_UTC = "2026-06-14"
DEFAULT_STARTED_AT = "2026-06-14T00:00:00Z"
DEFAULT_FIXTURE_ROOT = Path("experiments/fixtures/local_sources")


def build_source_refresh_summary_payload(
    *,
    fixture_root: Path = DEFAULT_FIXTURE_ROOT,
    end_day_utc: str = DEFAULT_END_DAY_UTC,
    started_at: str = DEFAULT_STARTED_AT,
) -> dict:
    return build_primary_refresh_command_payload(
        codex_jsonl_root=fixture_root / "codex",
        claude_code_jsonl_root=fixture_root / "claude_code",
        end_day_utc=end_day_utc,
        started_at=started_at,
    )


def write_source_refresh_summary(
    output_path: Path,
    *,
    fixture_root: Path = DEFAULT_FIXTURE_ROOT,
    end_day_utc: str = DEFAULT_END_DAY_UTC,
    started_at: str = DEFAULT_STARTED_AT,
) -> None:
    payload = build_source_refresh_summary_payload(
        fixture_root=fixture_root,
        end_day_utc=end_day_utc,
        started_at=started_at,
    )
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_source_refresh_error_payload() -> dict:
    return build_primary_refresh_command_response_from_mapping(
        {
            "codex_jsonl_root": "C:/Users/example/secret/codex",
            "end_day_utc": "2026-6-14",
        }
    )


def write_source_refresh_error(output_path: Path) -> None:
    output_path.write_text(
        json.dumps(build_source_refresh_error_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the synthetic PR5 source refresh-summary payload.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path for the generated JSON payload.",
    )
    parser.add_argument(
        "--fixture-root",
        default=DEFAULT_FIXTURE_ROOT,
        type=Path,
        help="Root containing synthetic local source fixtures.",
    )
    parser.add_argument(
        "--end-day-utc",
        default=DEFAULT_END_DAY_UTC,
        help="Inclusive rolling 7-day end day in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--started-at",
        default=DEFAULT_STARTED_AT,
        help="Synthetic refresh start timestamp.",
    )
    parser.add_argument(
        "--error-sample",
        action="store_true",
        help="Export the deterministic invalid-request error payload.",
    )
    args = parser.parse_args(argv)

    if args.error_sample:
        write_source_refresh_error(args.output)
        return 0

    write_source_refresh_summary(
        args.output,
        fixture_root=args.fixture_root,
        end_day_utc=args.end_day_utc,
        started_at=args.started_at,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
