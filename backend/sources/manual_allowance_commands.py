"""Command-shaped helpers for manual allowance window persistence."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from backend.core import (
    ALLOWANCE_UNITS,
    SOURCE_KINDS,
    AllowanceWindow,
    ContractError,
    allowance_window_to_dict,
    normalize_utc_timestamp,
)
from backend.storage import (
    build_storage_summary_payload,
    connect_database,
    initialize_schema,
    replace_allowance_window_for_source_kind,
)


SAVE_MANUAL_ALLOWANCE_COMMAND_NAME = "save_manual_allowance_window"
MANUAL_ALLOWANCE_SOURCE_ID_SUFFIX = "manual_allowance"


@dataclass(frozen=True)
class ManualAllowanceCommandRequest:
    end_day_utc: str
    allowance_window: AllowanceWindow


class ManualAllowanceCommandError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_manual_allowance_request",
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def manual_allowance_command_error_to_payload(
    exc: ManualAllowanceCommandError,
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


def manual_allowance_command_request_from_mapping(
    data: Mapping[str, Any],
) -> ManualAllowanceCommandRequest:
    allowed_keys = {
        "end_day_utc",
        "source_kind",
        "unit",
        "window_start",
        "window_end",
        "reset_at",
        "limit_amount",
        "used_amount",
        "remaining_amount",
    }
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise ManualAllowanceCommandError(
            f"unsupported manual allowance fields: {_safe_unknown_keys(unknown_keys)}"
        )

    end_day_utc = data.get("end_day_utc")
    if not isinstance(end_day_utc, str) or not end_day_utc.strip():
        raise ManualAllowanceCommandError(
            "end_day_utc is required",
            field="end_day_utc",
        )

    source_kind = _source_kind(data.get("source_kind"))
    unit = _unit(data.get("unit"))
    window_start = _optional_timestamp(data.get("window_start"), "window_start")
    window_end = _optional_timestamp(data.get("window_end"), "window_end")
    if window_start and window_end and window_start > window_end:
        raise ManualAllowanceCommandError(
            "window_end must be after window_start",
            field="window_end",
        )

    try:
        allowance_window = AllowanceWindow(
            source_kind=source_kind,
            source_id=f"{source_kind}:{MANUAL_ALLOWANCE_SOURCE_ID_SUFFIX}",
            status="manual",
            unit=unit,
            window_start=window_start,
            window_end=window_end,
            reset_at=_optional_timestamp(data.get("reset_at"), "reset_at"),
            limit_amount=_required_positive_number(data.get("limit_amount"), "limit_amount"),
            used_amount=_optional_number(data.get("used_amount"), "used_amount"),
            remaining_amount=_optional_number(data.get("remaining_amount"), "remaining_amount"),
        )
    except ContractError as exc:
        raise ManualAllowanceCommandError(str(exc), field="allowance_window") from exc

    return ManualAllowanceCommandRequest(
        end_day_utc=_normalize_end_day_utc(end_day_utc),
        allowance_window=allowance_window,
    )


def manual_allowance_command_request_from_json(
    text: str,
) -> ManualAllowanceCommandRequest:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ManualAllowanceCommandError(
            "manual allowance request must be valid JSON"
        )
    if not isinstance(data, dict):
        raise ManualAllowanceCommandError(
            "manual allowance request must be a JSON object"
        )
    return manual_allowance_command_request_from_mapping(data)


def build_manual_allowance_command_payload_from_request(
    request: ManualAllowanceCommandRequest,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    return build_manual_allowance_command_payload(
        request.allowance_window,
        end_day_utc=request.end_day_utc,
        connection=connection,
    )


def build_manual_allowance_command_response_from_mapping(
    data: Mapping[str, Any],
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    try:
        request = manual_allowance_command_request_from_mapping(data)
    except ManualAllowanceCommandError as exc:
        return manual_allowance_command_error_to_payload(exc)
    return build_manual_allowance_command_payload_from_request(
        request,
        connection=connection,
    )


def build_manual_allowance_command_response_from_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    try:
        request = manual_allowance_command_request_from_json(text)
    except ManualAllowanceCommandError as exc:
        return manual_allowance_command_error_to_payload(exc)
    return build_manual_allowance_command_payload_from_request(
        request,
        connection=connection,
    )


def build_manual_allowance_command_response_payload(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        request = manual_allowance_command_request_from_json(text)
    except ManualAllowanceCommandError as exc:
        return manual_allowance_command_error_to_payload(exc)

    if connection is not None and database_path is not None:
        return manual_allowance_command_error_to_payload(
            ManualAllowanceCommandError("manual allowance connection is ambiguous")
        )
    if connection is not None or database_path is None:
        return build_manual_allowance_command_payload_from_request(
            request,
            connection=connection,
        )

    try:
        file_connection = connect_database(database_path)
    except sqlite3.Error:
        return manual_allowance_command_error_to_payload(
            ManualAllowanceCommandError(
                "manual allowance database could not be opened",
                code="manual_allowance_unavailable",
                field="database_path",
            )
        )
    try:
        return build_manual_allowance_command_payload_from_request(
            request,
            connection=file_connection,
        )
    finally:
        file_connection.close()


def build_manual_allowance_command_response_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
) -> str:
    return json.dumps(
        build_manual_allowance_command_response_payload(
            text,
            connection=connection,
            database_path=database_path,
        ),
        sort_keys=True,
    ) + "\n"


def build_manual_allowance_command_payload(
    allowance_window: AllowanceWindow,
    *,
    end_day_utc: str,
    connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    active_connection = connection or sqlite3.connect(":memory:")
    initialize_schema(active_connection)
    try:
        replace_allowance_window_for_source_kind(active_connection, allowance_window)
    except sqlite3.Error:
        return manual_allowance_command_error_to_payload(
            ManualAllowanceCommandError(
                "manual allowance database could not be written",
                code="manual_allowance_unavailable",
                field="database_path",
            )
        )

    return {
        "allowance_window": allowance_window_to_dict(allowance_window),
        "storage_summary": build_storage_summary_payload(
            active_connection,
            end_day_utc=end_day_utc,
            generated_from="backend.sources.manual_allowance_commands",
        ),
    }


def _source_kind(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManualAllowanceCommandError(
            "source_kind is required",
            field="source_kind",
        )
    source_kind = value.strip()
    if source_kind not in SOURCE_KINDS:
        raise ManualAllowanceCommandError(
            "unknown source_kind",
            field="source_kind",
        )
    return source_kind


def _unit(value: Any) -> str:
    if value is None:
        return "tokens"
    if not isinstance(value, str) or not value.strip():
        raise ManualAllowanceCommandError(
            "unit must be a non-empty string",
            field="unit",
        )
    unit = value.strip()
    if unit not in ALLOWANCE_UNITS:
        raise ManualAllowanceCommandError(
            "unknown allowance unit",
            field="unit",
        )
    return unit


def _required_positive_number(value: Any, field_name: str) -> float:
    number = _optional_number(value, field_name)
    if number is None:
        raise ManualAllowanceCommandError(
            f"{field_name} is required",
            field=field_name,
        )
    if number <= 0:
        raise ManualAllowanceCommandError(
            f"{field_name} must be positive",
            field=field_name,
        )
    return number


def _optional_number(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManualAllowanceCommandError(
            f"{field_name} must be a number",
            field=field_name,
        )
    if value < 0:
        raise ManualAllowanceCommandError(
            f"{field_name} must be non-negative",
            field=field_name,
        )
    return value


def _optional_timestamp(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ManualAllowanceCommandError(
            f"{field_name} must be a non-empty string when provided",
            field=field_name,
        )
    try:
        return normalize_utc_timestamp(value)
    except ContractError as exc:
        raise ManualAllowanceCommandError(
            f"{field_name} must be ISO-8601",
            field=field_name,
        ) from exc


def _normalize_end_day_utc(value: str) -> str:
    text = value.strip()
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ManualAllowanceCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        ) from exc
    if parsed.isoformat() != text:
        raise ManualAllowanceCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        )
    return text


def _safe_unknown_keys(keys: set[Any]) -> list[str]:
    safe_keys = []
    for key in sorted(keys, key=lambda item: str(type(item)) + str(item)):
        if (
            isinstance(key, str)
            and key.replace("_", "").isalnum()
            and len(key) <= 64
        ):
            safe_keys.append(key)
        else:
            safe_keys.append("<unsupported>")
    return safe_keys
