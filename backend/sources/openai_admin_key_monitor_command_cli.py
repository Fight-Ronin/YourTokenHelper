"""stdin/stdout boundary for OpenAI Admin API key monitor payloads."""

from __future__ import annotations

import sys
from typing import TextIO

from backend.sources.openai_admin_key_monitor_commands import (
    build_openai_admin_key_monitor_command_response_json,
)


def run_openai_admin_key_monitor_command_io(
    stdin: TextIO,
    stdout: TextIO,
) -> int:
    stdout.write(
        build_openai_admin_key_monitor_command_response_json(
            stdin.read(),
        )
    )
    return 0


def main() -> int:
    return run_openai_admin_key_monitor_command_io(sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
