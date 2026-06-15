"""stdin/stdout boundary for live API provider billing sync."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import TextIO

from backend.sources.api_provider_billing_sync_commands import (
    FetchProviderBillingPayload,
    build_api_provider_billing_sync_command_response_json,
)


API_PROVIDER_BILLING_SYNC_DATABASE_PATH_ENV_VAR = "YTH_REFRESH_DATABASE_PATH"


def run_api_provider_billing_sync_command_io(
    stdin: TextIO,
    stdout: TextIO,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
    fetch_provider_billing: FetchProviderBillingPayload | None = None,
) -> int:
    stdout.write(
        build_api_provider_billing_sync_command_response_json(
            stdin.read(),
            connection=connection,
            database_path=database_path,
            fetch_provider_billing=fetch_provider_billing,
        )
    )
    return 0


def main() -> int:
    return run_api_provider_billing_sync_command_io(
        sys.stdin,
        sys.stdout,
        database_path=api_provider_billing_sync_database_path_from_env(),
    )


def api_provider_billing_sync_database_path_from_env() -> Path | None:
    value = os.environ.get(API_PROVIDER_BILLING_SYNC_DATABASE_PATH_ENV_VAR)
    if value is None or not value.strip():
        return None
    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
