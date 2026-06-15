"""Unified stdin/stdout boundary for the packaged backend sidecar."""

from __future__ import annotations

import os
import sys
from typing import TextIO

from backend.sources.api_provider_billing_sync_command_cli import (
    api_provider_billing_sync_database_path_from_env,
    run_api_provider_billing_sync_command_io,
)
from backend.sources.api_provider_billing_sync_commands import (
    SYNC_API_PROVIDER_BILLING_COMMAND_NAME,
)
from backend.sources.openai_admin_key_probe import OPENAI_ADMIN_KEY_ENV_VAR
from backend.sources.commands import PRIMARY_REFRESH_COMMAND_NAME
from backend.sources.manual_allowance_command_cli import (
    manual_allowance_database_path_from_env,
    run_manual_allowance_command_io,
)
from backend.sources.manual_allowance_commands import SAVE_MANUAL_ALLOWANCE_COMMAND_NAME
from backend.sources.refresh_command_cli import (
    refresh_database_path_from_env,
    run_primary_refresh_command_io,
)
from backend.storage.summary_command_cli import (
    LOAD_STORAGE_SUMMARY_COMMAND_NAME,
    load_storage_summary_database_path_from_env,
    run_load_storage_summary_command_io,
)


def run_sidecar_command_io(
    argv: list[str],
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    if len(argv) < 2:
        stderr.write("backend command is required\n")
        return 2

    command_name = argv[1]
    if command_name != SYNC_API_PROVIDER_BILLING_COMMAND_NAME:
        os.environ.pop(OPENAI_ADMIN_KEY_ENV_VAR, None)

    if command_name == PRIMARY_REFRESH_COMMAND_NAME:
        return run_primary_refresh_command_io(
            stdin,
            stdout,
            database_path=refresh_database_path_from_env(),
        )
    if command_name == LOAD_STORAGE_SUMMARY_COMMAND_NAME:
        return run_load_storage_summary_command_io(
            stdin,
            stdout,
            database_path=load_storage_summary_database_path_from_env(),
        )
    if command_name == SAVE_MANUAL_ALLOWANCE_COMMAND_NAME:
        return run_manual_allowance_command_io(
            stdin,
            stdout,
            database_path=manual_allowance_database_path_from_env(),
        )
    if command_name == SYNC_API_PROVIDER_BILLING_COMMAND_NAME:
        return run_api_provider_billing_sync_command_io(
            stdin,
            stdout,
            database_path=api_provider_billing_sync_database_path_from_env(),
        )

    stderr.write("unknown backend command\n")
    return 2


def main() -> int:
    return run_sidecar_command_io(sys.argv, sys.stdin, sys.stdout, sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
