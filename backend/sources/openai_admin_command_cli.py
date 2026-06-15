"""stdin/stdout boundary for the OpenAI Admin usage/cost sync command."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import TextIO

from backend.sources.openai_admin_commands import (
    build_openai_admin_sync_command_response_json,
)

OPENAI_ADMIN_SYNC_DATABASE_PATH_ENV_VAR = "YTH_REFRESH_DATABASE_PATH"


def run_openai_admin_sync_command_io(
    stdin: TextIO,
    stdout: TextIO,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> int:
    stdout.write(
        build_openai_admin_sync_command_response_json(
            stdin.read(),
            connection=connection,
            database_path=database_path,
        )
    )
    return 0


def main() -> int:
    return run_openai_admin_sync_command_io(
        sys.stdin,
        sys.stdout,
        database_path=openai_admin_sync_database_path_from_env(),
    )


def openai_admin_sync_database_path_from_env() -> Path | None:
    value = os.environ.get(OPENAI_ADMIN_SYNC_DATABASE_PATH_ENV_VAR)
    if value is None or not value.strip():
        return None
    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
