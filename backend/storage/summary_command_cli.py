"""stdin/stdout boundary for reading the persisted storage summary."""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, TextIO

from backend.storage import build_storage_summary_payload, connect_database

LOAD_STORAGE_SUMMARY_COMMAND_NAME = "load_storage_summary"
LOAD_STORAGE_SUMMARY_DATABASE_PATH_ENV_VAR = "YTH_REFRESH_DATABASE_PATH"


@dataclass(frozen=True)
class LoadStorageSummaryRequest:
    end_day_utc: str


class LoadStorageSummaryCommandError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_storage_summary_request",
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def load_storage_summary_error_to_payload(
    exc: LoadStorageSummaryCommandError,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": str(exc),
        }
    }
    if exc.field is not None:
        payload["error"]["field"] = exc.field
    return payload


def load_storage_summary_request_from_mapping(
    data: Mapping[str, Any],
) -> LoadStorageSummaryRequest:
    allowed_keys = {"end_day_utc"}
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise LoadStorageSummaryCommandError(
            f"unsupported storage summary fields: {sorted(unknown_keys)}"
        )

    end_day_utc = data.get("end_day_utc")
    if not isinstance(end_day_utc, str) or not end_day_utc.strip():
        raise LoadStorageSummaryCommandError(
            "end_day_utc is required",
            field="end_day_utc",
        )
    return LoadStorageSummaryRequest(end_day_utc=_normalize_end_day_utc(end_day_utc))


def build_load_storage_summary_response_from_mapping(
    data: Mapping[str, Any],
    *,
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    try:
        request = load_storage_summary_request_from_mapping(data)
    except LoadStorageSummaryCommandError as exc:
        return load_storage_summary_error_to_payload(exc)
    return build_load_storage_summary_payload_from_request(
        request,
        connection=connection,
    )


def build_load_storage_summary_payload_from_request(
    request: LoadStorageSummaryRequest,
    *,
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    try:
        return build_storage_summary_payload(connection, end_day_utc=request.end_day_utc)
    except sqlite3.Error:
        return load_storage_summary_error_to_payload(
            storage_summary_unavailable("storage summary could not be read")
        )


def load_storage_summary_request_from_json(text: str) -> LoadStorageSummaryRequest:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise LoadStorageSummaryCommandError(
            "storage summary request must be valid JSON"
        )
    if not isinstance(data, dict):
        raise LoadStorageSummaryCommandError(
            "storage summary request must be a JSON object"
        )
    return load_storage_summary_request_from_mapping(data)


def build_load_storage_summary_response_from_json(
    text: str,
    *,
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    try:
        request = load_storage_summary_request_from_json(text)
    except LoadStorageSummaryCommandError as exc:
        return load_storage_summary_error_to_payload(exc)
    return build_load_storage_summary_payload_from_request(
        request,
        connection=connection,
    )


def build_load_storage_summary_response_payload(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        request = load_storage_summary_request_from_json(text)
    except LoadStorageSummaryCommandError as exc:
        return load_storage_summary_error_to_payload(exc)

    if connection is not None and database_path is not None:
        return load_storage_summary_error_to_payload(
            LoadStorageSummaryCommandError("storage summary connection is ambiguous")
        )
    if connection is not None:
        return build_load_storage_summary_payload_from_request(
            request,
            connection=connection,
        )
    if database_path is None:
        return load_storage_summary_error_to_payload(
            storage_summary_unavailable("storage summary database is unavailable")
        )

    path = Path(database_path)
    if not path.is_file():
        return load_storage_summary_error_to_payload(
            storage_summary_unavailable("storage summary database is unavailable")
        )

    try:
        file_connection = connect_database(path)
    except sqlite3.Error:
        return load_storage_summary_error_to_payload(
            storage_summary_unavailable("storage summary database could not be opened")
        )
    try:
        return build_load_storage_summary_payload_from_request(
            request,
            connection=file_connection,
        )
    finally:
        file_connection.close()


def build_load_storage_summary_response_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> str:
    return json.dumps(
        build_load_storage_summary_response_payload(
            text,
            connection=connection,
            database_path=database_path,
        ),
        sort_keys=True,
    ) + "\n"


def run_load_storage_summary_command_io(
    stdin: TextIO,
    stdout: TextIO,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> int:
    stdout.write(
        build_load_storage_summary_response_json(
            stdin.read(),
            connection=connection,
            database_path=database_path,
        )
    )
    return 0


def main() -> int:
    return run_load_storage_summary_command_io(
        sys.stdin,
        sys.stdout,
        database_path=load_storage_summary_database_path_from_env(),
    )


def load_storage_summary_database_path_from_env() -> Path | None:
    value = os.environ.get(LOAD_STORAGE_SUMMARY_DATABASE_PATH_ENV_VAR)
    if value is None or not value.strip():
        return None
    return Path(value)


def storage_summary_unavailable(message: str) -> LoadStorageSummaryCommandError:
    return LoadStorageSummaryCommandError(
        message,
        code="storage_summary_unavailable",
        field="database_path",
    )


def _normalize_end_day_utc(value: str) -> str:
    text = value.strip()
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise LoadStorageSummaryCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        ) from exc
    if parsed.isoformat() != text:
        raise LoadStorageSummaryCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        )
    return text


if __name__ == "__main__":
    raise SystemExit(main())
