"""stdin/stdout boundary for the manual source refresh command."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import TextIO

from backend.sources.commands import build_primary_refresh_command_response_json

REFRESH_DATABASE_PATH_ENV_VAR = "YTH_REFRESH_DATABASE_PATH"


def run_primary_refresh_command_io(
    stdin: TextIO,
    stdout: TextIO,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> int:
    stdout.write(
        build_primary_refresh_command_response_json(
            stdin.read(),
            connection=connection,
            database_path=database_path,
        )
    )
    return 0


def main() -> int:
    return run_primary_refresh_command_io(
        sys.stdin,
        sys.stdout,
        database_path=refresh_database_path_from_env(),
    )


def refresh_database_path_from_env() -> Path | None:
    value = os.environ.get(REFRESH_DATABASE_PATH_ENV_VAR)
    if value is None or not value.strip():
        return None
    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
