"""Command-shaped helpers for source refresh operations."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from backend.core import ContractError, normalize_utc_timestamp
from backend.sources.discovery import JsonlSourceCandidate
from backend.sources.refresh import refresh_sources_summary_payload
from backend.sources.registry import build_primary_source_adapters
from backend.storage import connect_database, initialize_schema


PRIMARY_REFRESH_COMMAND_NAME = "refresh_sources_manual"


@dataclass(frozen=True)
class PrimaryRefreshCommandRequest:
    end_day_utc: str
    codex_jsonl_root: Path | None = None
    claude_code_jsonl_root: Path | None = None
    started_at: str | None = None


class PrimaryRefreshCommandError(ValueError):
    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.code = "invalid_refresh_request"
        self.field = field


def primary_refresh_command_error_to_payload(
    exc: PrimaryRefreshCommandError,
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


def primary_refresh_command_request_from_mapping(
    data: Mapping[str, Any],
) -> PrimaryRefreshCommandRequest:
    allowed_keys = {
        "end_day_utc",
        "codex_jsonl_root",
        "claude_code_jsonl_root",
        "started_at",
    }
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise PrimaryRefreshCommandError(
            f"unsupported refresh command fields: {sorted(unknown_keys)}"
        )

    end_day_utc = data.get("end_day_utc")
    if not isinstance(end_day_utc, str) or not end_day_utc.strip():
        raise PrimaryRefreshCommandError("end_day_utc is required", field="end_day_utc")
    end_day_utc = _normalize_end_day_utc(end_day_utc)

    started_at = data.get("started_at")
    if started_at is not None and (not isinstance(started_at, str) or not started_at.strip()):
        raise PrimaryRefreshCommandError(
            "started_at must be a non-empty string when provided",
            field="started_at",
        )
    if started_at is not None:
        try:
            started_at = normalize_utc_timestamp(started_at)
        except ContractError as exc:
            raise PrimaryRefreshCommandError(
                "started_at must be ISO-8601",
                field="started_at",
            ) from exc

    return PrimaryRefreshCommandRequest(
        end_day_utc=end_day_utc,
        codex_jsonl_root=_optional_path(data.get("codex_jsonl_root"), "codex_jsonl_root"),
        claude_code_jsonl_root=_optional_path(
            data.get("claude_code_jsonl_root"),
            "claude_code_jsonl_root",
        ),
        started_at=started_at,
    )


def build_primary_refresh_command_payload_from_request(
    request: PrimaryRefreshCommandRequest,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    return build_primary_refresh_command_payload(
        connection=connection,
        codex_jsonl_root=request.codex_jsonl_root,
        claude_code_jsonl_root=request.claude_code_jsonl_root,
        end_day_utc=request.end_day_utc,
        started_at=request.started_at,
    )


def build_primary_refresh_command_response_from_mapping(
    data: Mapping[str, Any],
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    try:
        request = primary_refresh_command_request_from_mapping(data)
    except PrimaryRefreshCommandError as exc:
        return primary_refresh_command_error_to_payload(exc)
    return build_primary_refresh_command_payload_from_request(
        request,
        connection=connection,
    )


def build_primary_refresh_command_response_from_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return primary_refresh_command_error_to_payload(
            PrimaryRefreshCommandError("refresh request must be valid JSON")
        )
    if not isinstance(data, dict):
        return primary_refresh_command_error_to_payload(
            PrimaryRefreshCommandError("refresh request must be a JSON object")
        )
    return build_primary_refresh_command_response_from_mapping(
        data,
        connection=connection,
    )


def build_primary_refresh_command_response_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> str:
    payload = build_primary_refresh_command_response_payload(
        text,
        connection=connection,
        database_path=database_path,
    )
    return json.dumps(payload, sort_keys=True) + "\n"


def build_primary_refresh_command_response_payload(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    if connection is not None and database_path is not None:
        return primary_refresh_command_error_to_payload(
            PrimaryRefreshCommandError("refresh connection is ambiguous")
        )
    if database_path is None:
        return build_primary_refresh_command_response_from_json(
            text,
            connection=connection,
        )

    try:
        file_connection = connect_database(database_path)
    except sqlite3.Error:
        return primary_refresh_command_error_to_payload(
            PrimaryRefreshCommandError(
                "refresh database could not be opened",
                field="database_path",
            )
        )
    try:
        return build_primary_refresh_command_response_from_json(
            text,
            connection=file_connection,
        )
    finally:
        file_connection.close()


def build_primary_refresh_command_payload(
    *,
    end_day_utc: str,
    codex_jsonl_root: Path | None = None,
    claude_code_jsonl_root: Path | None = None,
    started_at: str | None = None,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    active_connection = connection or sqlite3.connect(":memory:")
    initialize_schema(active_connection)
    return refresh_sources_summary_payload(
        active_connection,
        build_primary_source_adapters(
            primary_jsonl_candidates(
                codex_jsonl_root=codex_jsonl_root,
                claude_code_jsonl_root=claude_code_jsonl_root,
            )
        ),
        end_day_utc=end_day_utc,
        started_at=started_at,
    )


def primary_jsonl_candidates(
    *,
    codex_jsonl_root: Path | None = None,
    claude_code_jsonl_root: Path | None = None,
) -> list[JsonlSourceCandidate]:
    candidates: list[JsonlSourceCandidate] = []
    if codex_jsonl_root is not None:
        candidates.append(JsonlSourceCandidate("codex", codex_jsonl_root))
    if claude_code_jsonl_root is not None:
        candidates.append(JsonlSourceCandidate("claude_code", claude_code_jsonl_root))
    return candidates


def _optional_path(value: Any, field_name: str) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise PrimaryRefreshCommandError(
            f"{field_name} must be a non-empty string when provided",
            field=field_name,
        )
    return Path(value)


def _normalize_end_day_utc(value: str) -> str:
    text = value.strip()
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise PrimaryRefreshCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        ) from exc
    if parsed.isoformat() != text:
        raise PrimaryRefreshCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        )
    return text
