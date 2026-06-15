"""Command-shaped helpers for live OpenAI Admin API key probing."""

from __future__ import annotations

import datetime as dt
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.core import ContractError
from backend.sources.openai_admin_key_monitor import (
    normalize_monitor_timestamp,
    openai_admin_key_monitor_result_to_payload,
)
from backend.sources.openai_admin_key_probe import (
    FetchAdminApiKeysPayload,
    OPENAI_ADMIN_KEY_ENV_VAR,
    probe_openai_admin_api_key,
)


OPENAI_ADMIN_KEY_PROBE_COMMAND_NAME = "probe_openai_admin_api_key"


@dataclass(frozen=True)
class OpenAIAdminKeyProbeCommandRequest:
    checked_at: str


class OpenAIAdminKeyProbeCommandError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_openai_admin_key_probe_request",
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def openai_admin_key_probe_command_error_to_payload(
    exc: OpenAIAdminKeyProbeCommandError,
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


def openai_admin_key_probe_command_request_from_mapping(
    data: Mapping[str, Any],
) -> OpenAIAdminKeyProbeCommandRequest:
    allowed_keys = {"checked_at"}
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise OpenAIAdminKeyProbeCommandError(
            f"unsupported OpenAI Admin key probe fields: {sorted(unknown_keys)}"
        )

    checked_at = data.get("checked_at")
    if checked_at is None:
        checked_at = _utc_now()
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise OpenAIAdminKeyProbeCommandError(
            "checked_at must be a non-empty string when provided",
            field="checked_at",
        )
    try:
        checked_at = normalize_monitor_timestamp(checked_at)
    except ContractError as exc:
        raise OpenAIAdminKeyProbeCommandError(
            "checked_at must be ISO-8601",
            field="checked_at",
        ) from exc

    return OpenAIAdminKeyProbeCommandRequest(checked_at=checked_at)


def build_openai_admin_key_probe_command_payload_from_request(
    request: OpenAIAdminKeyProbeCommandRequest,
    *,
    env: Mapping[str, str] | None = None,
    fetch_admin_api_keys: FetchAdminApiKeysPayload | None = None,
) -> dict[str, Any]:
    api_key = _admin_api_key_from_env(os.environ if env is None else env)
    if api_key is None:
        return openai_admin_key_probe_command_error_to_payload(
            OpenAIAdminKeyProbeCommandError(
                "OpenAI Admin API key is not configured",
                code="openai_admin_key_probe_unavailable",
                field="environment",
            )
        )

    try:
        result = probe_openai_admin_api_key(
            api_key,
            checked_at=request.checked_at,
            fetch_admin_api_keys=fetch_admin_api_keys,
        )
    except ContractError:
        return openai_admin_key_probe_command_error_to_payload(
            OpenAIAdminKeyProbeCommandError(
                "OpenAI Admin API key probe returned an unsupported response",
                code="openai_admin_key_probe_unavailable",
                field="endpoint",
            )
        )
    return {"monitor_result": openai_admin_key_monitor_result_to_payload(result)}


def build_openai_admin_key_probe_command_response_from_mapping(
    data: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    fetch_admin_api_keys: FetchAdminApiKeysPayload | None = None,
) -> dict[str, Any]:
    try:
        request = openai_admin_key_probe_command_request_from_mapping(data)
    except OpenAIAdminKeyProbeCommandError as exc:
        return openai_admin_key_probe_command_error_to_payload(exc)
    return build_openai_admin_key_probe_command_payload_from_request(
        request,
        env=env,
        fetch_admin_api_keys=fetch_admin_api_keys,
    )


def build_openai_admin_key_probe_command_response_from_json(
    text: str,
    *,
    env: Mapping[str, str] | None = None,
    fetch_admin_api_keys: FetchAdminApiKeysPayload | None = None,
) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return openai_admin_key_probe_command_error_to_payload(
            OpenAIAdminKeyProbeCommandError(
                "OpenAI Admin key probe request must be valid JSON"
            )
        )
    if not isinstance(data, dict):
        return openai_admin_key_probe_command_error_to_payload(
            OpenAIAdminKeyProbeCommandError(
                "OpenAI Admin key probe request must be a JSON object"
            )
        )
    return build_openai_admin_key_probe_command_response_from_mapping(
        data,
        env=env,
        fetch_admin_api_keys=fetch_admin_api_keys,
    )


def build_openai_admin_key_probe_command_response_json(
    text: str,
    *,
    env: Mapping[str, str] | None = None,
    fetch_admin_api_keys: FetchAdminApiKeysPayload | None = None,
) -> str:
    return json.dumps(
        build_openai_admin_key_probe_command_response_from_json(
            text,
            env=env,
            fetch_admin_api_keys=fetch_admin_api_keys,
        ),
        sort_keys=True,
    ) + "\n"


def _admin_api_key_from_env(env: Mapping[str, str]) -> str | None:
    value = env.get(OPENAI_ADMIN_KEY_ENV_VAR)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
