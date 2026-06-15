"""Command-shaped helpers for OpenAI Admin usage/cost ingestion."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from backend.core import ContractError, normalize_utc_timestamp
from backend.sources.openai_admin import (
    OpenAIAdminSyncResult,
    sync_openai_admin_usage_cost_payload,
)
from backend.storage import build_storage_summary_payload, connect_database, initialize_schema


OPENAI_ADMIN_SYNC_COMMAND_NAME = "sync_openai_admin_usage_cost"


@dataclass(frozen=True)
class OpenAIAdminSyncCommandRequest:
    end_day_utc: str
    payload: Mapping[str, Any]
    started_at: str | None = None


class OpenAIAdminSyncCommandError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_openai_admin_sync_request",
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def openai_admin_sync_command_error_to_payload(
    exc: OpenAIAdminSyncCommandError,
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


def openai_admin_sync_command_request_from_mapping(
    data: Mapping[str, Any],
) -> OpenAIAdminSyncCommandRequest:
    allowed_keys = {"end_day_utc", "payload", "started_at"}
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise OpenAIAdminSyncCommandError(
            f"unsupported OpenAI Admin sync fields: {sorted(unknown_keys)}"
        )

    end_day_utc = data.get("end_day_utc")
    if not isinstance(end_day_utc, str) or not end_day_utc.strip():
        raise OpenAIAdminSyncCommandError(
            "end_day_utc is required",
            field="end_day_utc",
        )
    end_day_utc = _normalize_end_day_utc(end_day_utc)

    payload = data.get("payload")
    if not isinstance(payload, Mapping):
        raise OpenAIAdminSyncCommandError(
            "payload must be a JSON object",
            field="payload",
        )

    started_at = data.get("started_at")
    if started_at is not None and (not isinstance(started_at, str) or not started_at.strip()):
        raise OpenAIAdminSyncCommandError(
            "started_at must be a non-empty string when provided",
            field="started_at",
        )
    if started_at is not None:
        try:
            started_at = normalize_utc_timestamp(started_at)
        except ContractError as exc:
            raise OpenAIAdminSyncCommandError(
                "started_at must be ISO-8601",
                field="started_at",
            ) from exc

    return OpenAIAdminSyncCommandRequest(
        end_day_utc=end_day_utc,
        payload=payload,
        started_at=started_at,
    )


def openai_admin_sync_command_request_from_json(
    text: str,
) -> OpenAIAdminSyncCommandRequest:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise OpenAIAdminSyncCommandError("OpenAI Admin sync request must be valid JSON")
    if not isinstance(data, dict):
        raise OpenAIAdminSyncCommandError("OpenAI Admin sync request must be a JSON object")
    return openai_admin_sync_command_request_from_mapping(data)


def build_openai_admin_sync_command_payload_from_request(
    request: OpenAIAdminSyncCommandRequest,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    return build_openai_admin_sync_command_payload(
        payload=request.payload,
        end_day_utc=request.end_day_utc,
        started_at=request.started_at,
        connection=connection,
    )


def build_openai_admin_sync_command_response_from_mapping(
    data: Mapping[str, Any],
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    try:
        request = openai_admin_sync_command_request_from_mapping(data)
    except OpenAIAdminSyncCommandError as exc:
        return openai_admin_sync_command_error_to_payload(exc)
    return build_openai_admin_sync_command_payload_from_request(
        request,
        connection=connection,
    )


def build_openai_admin_sync_command_response_from_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    try:
        request = openai_admin_sync_command_request_from_json(text)
    except OpenAIAdminSyncCommandError as exc:
        return openai_admin_sync_command_error_to_payload(exc)
    return build_openai_admin_sync_command_payload_from_request(
        request,
        connection=connection,
    )


def build_openai_admin_sync_command_response_payload(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        request = openai_admin_sync_command_request_from_json(text)
    except OpenAIAdminSyncCommandError as exc:
        return openai_admin_sync_command_error_to_payload(exc)

    if connection is not None and database_path is not None:
        return openai_admin_sync_command_error_to_payload(
            OpenAIAdminSyncCommandError("OpenAI Admin sync connection is ambiguous")
        )
    if connection is not None or database_path is None:
        return build_openai_admin_sync_command_payload_from_request(
            request,
            connection=connection,
        )

    try:
        file_connection = connect_database(database_path)
    except sqlite3.Error:
        return openai_admin_sync_command_error_to_payload(
            OpenAIAdminSyncCommandError(
                "OpenAI Admin sync database could not be opened",
                field="database_path",
            )
        )
    try:
        return build_openai_admin_sync_command_payload_from_request(
            request,
            connection=file_connection,
        )
    finally:
        file_connection.close()


def build_openai_admin_sync_command_response_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> str:
    return json.dumps(
        build_openai_admin_sync_command_response_payload(
            text,
            connection=connection,
            database_path=database_path,
        ),
        sort_keys=True,
    ) + "\n"


def build_openai_admin_sync_command_payload(
    *,
    payload: Mapping[str, Any],
    end_day_utc: str,
    started_at: str | None = None,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    active_connection = connection or sqlite3.connect(":memory:")
    initialize_schema(active_connection)
    try:
        result = sync_openai_admin_usage_cost_payload(
            active_connection,
            payload,
            end_day_utc=end_day_utc,
            started_at=started_at or _utc_now(),
        )
    except ContractError as exc:
        return openai_admin_sync_command_error_to_payload(
            OpenAIAdminSyncCommandError(str(exc), field="payload")
        )
    except sqlite3.Error:
        return openai_admin_sync_command_error_to_payload(
            OpenAIAdminSyncCommandError(
                "OpenAI Admin sync database could not be written",
                code="openai_admin_sync_unavailable",
                field="database_path",
            )
        )

    return {
        "sync_result": openai_admin_sync_result_to_payload(result),
        "storage_summary": build_storage_summary_payload(
            active_connection,
            end_day_utc=end_day_utc,
            generated_from="backend.sources.openai_admin_commands",
        ),
    }


def openai_admin_sync_result_to_payload(
    result: OpenAIAdminSyncResult,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_kind": result.state.source_kind,
        "source_id": result.state.source_id,
        "status": result.state.status,
        "confidence": result.state.confidence,
        "usage_events_seen": result.usage_events_seen,
        "cost_records_seen": result.cost_records_seen,
        "events_seen": result.usage_events_seen + result.cost_records_seen,
        "sync_run_id": result.sync_run_id,
    }
    if result.state.message:
        payload["message"] = result.state.message
    return payload


def _normalize_end_day_utc(value: str) -> str:
    text = value.strip()
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise OpenAIAdminSyncCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        ) from exc
    if parsed.isoformat() != text:
        raise OpenAIAdminSyncCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        )
    return text


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
