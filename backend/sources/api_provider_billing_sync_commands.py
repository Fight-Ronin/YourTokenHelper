"""Command-shaped helpers for live API provider billing sync."""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core import ContractError, normalize_utc_timestamp
from backend.sources.api_cost_provider import (
    api_cost_provider_status_for,
    api_cost_provider_status_to_payload,
    validate_api_cost_provider_id,
)
from backend.sources.openai_admin import OPENAI_API_COST_SOURCE_KIND
from backend.sources.openai_admin_commands import build_openai_admin_sync_command_payload
from backend.sources.openai_admin_key_probe import OPENAI_ADMIN_KEY_ENV_VAR
from backend.sources.openai_admin_live import fetch_openai_admin_usage_cost_payload
from backend.storage import connect_database


SYNC_API_PROVIDER_BILLING_COMMAND_NAME = "sync_api_provider_billing"

FetchProviderBillingPayload = Callable[..., Mapping[str, Any]]


@dataclass(frozen=True)
class ApiProviderBillingSyncCommandRequest:
    provider_id: str
    end_day_utc: str
    started_at: str | None = None


class ApiProviderBillingSyncCommandError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_api_provider_billing_sync_request",
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def api_provider_billing_sync_command_error_to_payload(
    exc: ApiProviderBillingSyncCommandError,
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


def api_provider_billing_sync_command_request_from_mapping(
    data: Mapping[str, Any],
) -> ApiProviderBillingSyncCommandRequest:
    allowed_keys = {"provider_id", "end_day_utc", "started_at"}
    unknown_keys = set(data) - allowed_keys
    if unknown_keys:
        raise ApiProviderBillingSyncCommandError(
            f"unsupported API provider billing sync fields: {sorted(unknown_keys)}"
        )

    provider_id = data.get("provider_id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ApiProviderBillingSyncCommandError(
            "provider_id is required",
            field="provider_id",
        )
    provider_id = provider_id.strip()
    try:
        validate_api_cost_provider_id(provider_id)
    except ContractError as exc:
        raise ApiProviderBillingSyncCommandError(
            "Unknown API cost provider",
            field="provider_id",
        ) from exc

    end_day_utc = data.get("end_day_utc")
    if not isinstance(end_day_utc, str) or not end_day_utc.strip():
        raise ApiProviderBillingSyncCommandError(
            "end_day_utc is required",
            field="end_day_utc",
        )
    end_day_utc = _normalize_end_day_utc(end_day_utc)

    started_at = data.get("started_at")
    if started_at is not None and (not isinstance(started_at, str) or not started_at.strip()):
        raise ApiProviderBillingSyncCommandError(
            "started_at must be a non-empty string when provided",
            field="started_at",
        )
    if started_at is not None:
        try:
            started_at = normalize_utc_timestamp(started_at)
        except ContractError as exc:
            raise ApiProviderBillingSyncCommandError(
                "started_at must be ISO-8601",
                field="started_at",
            ) from exc

    return ApiProviderBillingSyncCommandRequest(
        provider_id=provider_id,
        end_day_utc=end_day_utc,
        started_at=started_at,
    )


def api_provider_billing_sync_command_request_from_json(
    text: str,
) -> ApiProviderBillingSyncCommandRequest:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ApiProviderBillingSyncCommandError(
            "API provider billing sync request must be valid JSON"
        )
    if not isinstance(data, dict):
        raise ApiProviderBillingSyncCommandError(
            "API provider billing sync request must be a JSON object"
        )
    return api_provider_billing_sync_command_request_from_mapping(data)


def build_api_provider_billing_sync_command_payload_from_request(
    request: ApiProviderBillingSyncCommandRequest,
    *,
    connection: sqlite3.Connection | None = None,
    env: Mapping[str, str] | None = None,
    fetch_provider_billing: FetchProviderBillingPayload | None = None,
) -> dict[str, Any]:
    if request.provider_id != OPENAI_API_COST_SOURCE_KIND:
        return api_provider_billing_sync_command_error_to_payload(
            ApiProviderBillingSyncCommandError(
                "Provider billing adapter has not been verified",
                code="api_provider_billing_sync_unavailable",
                field="provider_id",
            )
        )

    api_key = _admin_api_key_from_env(os.environ if env is None else env)
    if api_key is None:
        return api_provider_billing_sync_command_error_to_payload(
            ApiProviderBillingSyncCommandError(
                "OpenAI API provider credential is not configured",
                code="api_provider_billing_sync_unavailable",
                field="credential",
            )
        )

    fetcher = fetch_provider_billing or fetch_openai_admin_usage_cost_payload
    try:
        payload = fetcher(api_key, end_day_utc=request.end_day_utc)
    except ContractError:
        return api_provider_billing_sync_command_error_to_payload(
            ApiProviderBillingSyncCommandError(
                "API provider billing sync returned an unsupported response",
                code="api_provider_billing_sync_unavailable",
                field="endpoint",
            )
        )
    if not isinstance(payload, Mapping):
        return api_provider_billing_sync_command_error_to_payload(
            ApiProviderBillingSyncCommandError(
                "API provider billing sync returned an unsupported response",
                code="api_provider_billing_sync_unavailable",
                field="endpoint",
            )
        )

    sync_payload = build_openai_admin_sync_command_payload(
        payload=payload,
        end_day_utc=request.end_day_utc,
        started_at=request.started_at,
        connection=connection,
    )
    if "error" in sync_payload:
        return sync_payload

    sync_payload["endpoint_statuses"] = _endpoint_statuses_from_openai_payload(payload)
    sync_payload["provider_status"] = api_cost_provider_status_to_payload(
        api_cost_provider_status_for(
            request.provider_id,
            credential_configured=True,
            status=_provider_status_from_openai_payload(payload, sync_payload),
        )
    )
    return sync_payload


def build_api_provider_billing_sync_command_response_from_mapping(
    data: Mapping[str, Any],
    *,
    connection: sqlite3.Connection | None = None,
    env: Mapping[str, str] | None = None,
    fetch_provider_billing: FetchProviderBillingPayload | None = None,
) -> dict[str, Any]:
    try:
        request = api_provider_billing_sync_command_request_from_mapping(data)
    except ApiProviderBillingSyncCommandError as exc:
        return api_provider_billing_sync_command_error_to_payload(exc)
    return build_api_provider_billing_sync_command_payload_from_request(
        request,
        connection=connection,
        env=env,
        fetch_provider_billing=fetch_provider_billing,
    )


def build_api_provider_billing_sync_command_response_from_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    env: Mapping[str, str] | None = None,
    fetch_provider_billing: FetchProviderBillingPayload | None = None,
) -> dict[str, Any]:
    try:
        request = api_provider_billing_sync_command_request_from_json(text)
    except ApiProviderBillingSyncCommandError as exc:
        return api_provider_billing_sync_command_error_to_payload(exc)
    return build_api_provider_billing_sync_command_payload_from_request(
        request,
        connection=connection,
        env=env,
        fetch_provider_billing=fetch_provider_billing,
    )


def build_api_provider_billing_sync_command_response_payload(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    fetch_provider_billing: FetchProviderBillingPayload | None = None,
) -> dict[str, Any]:
    try:
        request = api_provider_billing_sync_command_request_from_json(text)
    except ApiProviderBillingSyncCommandError as exc:
        return api_provider_billing_sync_command_error_to_payload(exc)

    if connection is not None and database_path is not None:
        return api_provider_billing_sync_command_error_to_payload(
            ApiProviderBillingSyncCommandError(
                "API provider billing sync connection is ambiguous"
            )
        )
    if connection is not None or database_path is None:
        return build_api_provider_billing_sync_command_payload_from_request(
            request,
            connection=connection,
            env=env,
            fetch_provider_billing=fetch_provider_billing,
        )

    try:
        file_connection = connect_database(database_path)
    except sqlite3.Error:
        return api_provider_billing_sync_command_error_to_payload(
            ApiProviderBillingSyncCommandError(
                "API provider billing sync database could not be opened",
                code="api_provider_billing_sync_unavailable",
                field="database_path",
            )
        )
    try:
        return build_api_provider_billing_sync_command_payload_from_request(
            request,
            connection=file_connection,
            env=env,
            fetch_provider_billing=fetch_provider_billing,
        )
    finally:
        file_connection.close()


def build_api_provider_billing_sync_command_response_json(
    text: str,
    *,
    connection: sqlite3.Connection | None = None,
    database_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    fetch_provider_billing: FetchProviderBillingPayload | None = None,
) -> str:
    return json.dumps(
        build_api_provider_billing_sync_command_response_payload(
            text,
            connection=connection,
            database_path=database_path,
            env=env,
            fetch_provider_billing=fetch_provider_billing,
        ),
        sort_keys=True,
    ) + "\n"


def _provider_status_from_openai_payload(
    payload: Mapping[str, Any],
    sync_payload: Mapping[str, Any],
) -> str:
    endpoint_statuses = set(_endpoint_statuses_from_openai_payload(payload).values())
    if "invalid_key" in endpoint_statuses:
        return "invalid_key"
    if "permission_denied" in endpoint_statuses:
        return "permission_denied"
    if "rate_limited" in endpoint_statuses:
        return "rate_limited"
    if "unavailable" in endpoint_statuses:
        return "unavailable"

    sync_result = sync_payload.get("sync_result")
    sync_status = sync_result.get("status") if isinstance(sync_result, Mapping) else None
    if sync_status == "ready":
        return "ready"
    if sync_status == "permission_denied":
        return "permission_denied"
    return "unavailable"


def _endpoint_statuses_from_openai_payload(payload: Mapping[str, Any]) -> dict[str, str]:
    return {
        "usage": _endpoint_status_from_openai_payload(payload.get("usage")),
        "costs": _endpoint_status_from_openai_payload(payload.get("costs")),
    }


def _endpoint_status_from_openai_payload(endpoint: Any) -> str:
    if not isinstance(endpoint, Mapping):
        return "unavailable"
    error_payload = endpoint.get("error")
    if isinstance(error_payload, Mapping):
        status = error_payload.get("status")
        if status == 401:
            return "invalid_key"
        if status == 403:
            return "permission_denied"
        if status == 429:
            return "rate_limited"
        return "unavailable"
    if isinstance(endpoint.get("data"), list):
        return "ready"
    return "unavailable"


def _admin_api_key_from_env(env: Mapping[str, str]) -> str | None:
    value = env.get(OPENAI_ADMIN_KEY_ENV_VAR)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_end_day_utc(value: str) -> str:
    text = value.strip()
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ApiProviderBillingSyncCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        ) from exc
    if parsed.isoformat() != text:
        raise ApiProviderBillingSyncCommandError(
            "end_day_utc must be YYYY-MM-DD",
            field="end_day_utc",
        )
    return text
