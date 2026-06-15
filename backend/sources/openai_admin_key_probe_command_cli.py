"""stdin/stdout boundary for live OpenAI Admin API key probing."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import TextIO

from backend.sources.openai_admin_key_probe import FetchAdminApiKeysPayload
from backend.sources.openai_admin_key_probe_commands import (
    build_openai_admin_key_probe_command_response_json,
)


def run_openai_admin_key_probe_command_io(
    stdin: TextIO,
    stdout: TextIO,
    *,
    env: Mapping[str, str] | None = None,
    fetch_admin_api_keys: FetchAdminApiKeysPayload | None = None,
) -> int:
    stdout.write(
        build_openai_admin_key_probe_command_response_json(
            stdin.read(),
            env=env,
            fetch_admin_api_keys=fetch_admin_api_keys,
        )
    )
    return 0


def main() -> int:
    return run_openai_admin_key_probe_command_io(sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
