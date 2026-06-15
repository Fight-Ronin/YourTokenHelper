"""Command-shaped helpers for OpenAI Admin API key monitoring."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Any, Mapping

from backend.core import ContractError
from backend.sources.openai_admin_key_monitor import (
    OpenAIAdminKeyMonitorResult,
    openai_admin_key_monitor_from_payload,
    openai_admin_key_monitor_result_to_payload,
    normalize_monitor_timestamp,
)


OPENAI_ADMIN_KEY_MONITOR_COMMAND_NAME = "monitor_openai_admin_api_key"


@dataclass(frozen=True)
class OpenAIAdminKeyMonitorCommandRequest:
    payload: Mapping[str, Any]
    checked_at: str


class OpenAIAdminKeyMonitorCommandError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_openai_admin_key_monitor_request",
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def openai_admin_key_monitor_command_error_to_payload(
    exc: OpenAIAdminKeyMonitorCommandError,
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


def openai_admin_key_monitor_command_request_from_mapping(
    data: Mapping[str, Any],
) -> OpenAIAdminKeyMonitorCommandRequest:
    allowed_keys = {"payload", "checked_at"}
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise OpenAIAdminKeyMonitorCommandError(
            f"unsupported OpenAI Admin key monitor fields: {sorted(unknown_keys)}"
        )

    payload = data.get("payload")
    if not isinstance(payload, Mapping):
        raise OpenAIAdminKeyMonitorCommandError(
            "payload must be a JSON object",
            field="payload",
        )

    checked_at = data.get("checked_at")
    if checked_at is None:
        checked_at = _utc_now()
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise OpenAIAdminKeyMonitorCommandError(
            "checked_at must be a non-empty string when provided",
            field="checked_at",
        )
    try:
        checked_at = normalize_monitor_timestamp(checked_at)
    except ContractError as exc:
        raise OpenAIAdminKeyMonitorCommandError(
            "checked_at must be ISO-8601",
            field="checked_at",
        ) from exc

    return OpenAIAdminKeyMonitorCommandRequest(
        payload=payload,
        checked_at=checked_at,
    )


def build_openai_admin_key_monitor_command_payload_from_request(
    request: OpenAIAdminKeyMonitorCommandRequest,
) -> dict[str, Any]:
    return build_openai_admin_key_monitor_command_payload(
        payload=request.payload,
        checked_at=request.checked_at,
    )


def build_openai_admin_key_monitor_command_payload(
    *,
    payload: Mapping[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    try:
        result = openai_admin_key_monitor_from_payload(
            payload,
            checked_at=checked_at,
        )
    except ContractError as exc:
        return openai_admin_key_monitor_command_error_to_payload(
            OpenAIAdminKeyMonitorCommandError(str(exc), field="payload")
        )
    return {
        "monitor_result": openai_admin_key_monitor_result_to_payload(result),
    }


def build_openai_admin_key_monitor_command_response_from_mapping(
    data: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        request = openai_admin_key_monitor_command_request_from_mapping(data)
    except OpenAIAdminKeyMonitorCommandError as exc:
        return openai_admin_key_monitor_command_error_to_payload(exc)
    return build_openai_admin_key_monitor_command_payload_from_request(request)


def build_openai_admin_key_monitor_command_response_from_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return openai_admin_key_monitor_command_error_to_payload(
            OpenAIAdminKeyMonitorCommandError(
                "OpenAI Admin key monitor request must be valid JSON"
            )
        )
    if not isinstance(data, dict):
        return openai_admin_key_monitor_command_error_to_payload(
            OpenAIAdminKeyMonitorCommandError(
                "OpenAI Admin key monitor request must be a JSON object"
            )
        )
    return build_openai_admin_key_monitor_command_response_from_mapping(data)


def build_openai_admin_key_monitor_command_response_json(text: str) -> str:
    return json.dumps(
        build_openai_admin_key_monitor_command_response_from_json(text),
        sort_keys=True,
    ) + "\n"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
