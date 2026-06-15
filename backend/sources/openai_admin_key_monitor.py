"""Redacted OpenAI Admin API key monitor payload parsing."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Mapping

from backend.core import ContractError
from backend.sources.openai_admin import hashed_identifier


OPENAI_ADMIN_KEY_MONITOR_SOURCE_ID = "openai_api_cost:admin_api_key_monitor"
OPENAI_ADMIN_KEY_MONITOR_STATUSES = (
    "ready",
    "invalid_key",
    "permission_denied",
    "rate_limited",
    "error",
)


@dataclass(frozen=True)
class OpenAIAdminKeyMonitorRecord:
    api_key_id: str
    created_at: str | None = None
    last_used_at: str | None = None


@dataclass(frozen=True)
class OpenAIAdminKeyMonitorResult:
    status: str
    confidence: str
    checked_at: str
    source_id: str = OPENAI_ADMIN_KEY_MONITOR_SOURCE_ID
    key_count: int = 0
    active_key_count: int = 0
    has_more: bool = False
    keys: tuple[OpenAIAdminKeyMonitorRecord, ...] = ()
    message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in OPENAI_ADMIN_KEY_MONITOR_STATUSES:
            raise ContractError(f"Unknown OpenAI Admin key monitor status: {self.status}")
        if self.confidence not in {"official", "unavailable"}:
            raise ContractError("OpenAI Admin key monitor confidence is invalid")
        if self.key_count < 0 or self.active_key_count < 0:
            raise ContractError("OpenAI Admin key counts must be non-negative")
        if self.active_key_count > self.key_count:
            raise ContractError("active key count cannot exceed key count")


def openai_admin_key_monitor_from_payload(
    payload: Mapping[str, Any],
    *,
    checked_at: str,
) -> OpenAIAdminKeyMonitorResult:
    envelope = payload.get("admin_api_keys")
    if not isinstance(envelope, Mapping):
        raise ContractError("OpenAI Admin API keys endpoint payload is required")

    error = envelope.get("error")
    if isinstance(error, Mapping):
        return _monitor_result_from_error(error, checked_at=checked_at)

    record = _record_from_admin_key(envelope)
    if record is not None:
        return OpenAIAdminKeyMonitorResult(
            status="ready",
            confidence="official",
            checked_at=normalize_monitor_timestamp(checked_at),
            key_count=1,
            active_key_count=1 if record.last_used_at is not None else 0,
            keys=(record,),
            message="OpenAI Admin API key retrieve is available.",
        )

    data = envelope.get("data")
    if data is None:
        raise ContractError(
            "OpenAI Admin API keys endpoint payload must include data or error"
        )
    if not isinstance(data, list):
        raise ContractError("OpenAI Admin API keys data must be a list")

    records = tuple(_records_from_admin_key_items(data))
    return OpenAIAdminKeyMonitorResult(
        status="ready",
        confidence="official",
        checked_at=normalize_monitor_timestamp(checked_at),
        key_count=len(records),
        active_key_count=sum(1 for record in records if record.last_used_at is not None),
        has_more=_optional_bool(envelope.get("has_more"), "has_more"),
        keys=records,
        message="OpenAI Admin API key listing is available.",
    )


def openai_admin_key_monitor_result_to_payload(
    result: OpenAIAdminKeyMonitorResult,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": result.source_id,
        "status": result.status,
        "confidence": result.confidence,
        "checked_at": result.checked_at,
        "key_count": result.key_count,
        "active_key_count": result.active_key_count,
        "has_more": result.has_more,
        "keys": [
            {
                "api_key_id": record.api_key_id,
                "created_at": record.created_at,
                "last_used_at": record.last_used_at,
            }
            for record in result.keys
        ],
    }
    if result.message:
        payload["message"] = result.message
    return payload


def normalize_monitor_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        raise ContractError("checked_at is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise ContractError("checked_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _monitor_result_from_error(
    error: Mapping[str, Any],
    *,
    checked_at: str,
) -> OpenAIAdminKeyMonitorResult:
    status_code = error.get("status")
    if status_code == 401:
        status = "invalid_key"
        message = "OpenAI Admin API key could not be authenticated."
    elif status_code == 403:
        status = "permission_denied"
        message = "OpenAI Admin API key listing access was denied."
    elif status_code == 429:
        status = "rate_limited"
        message = "OpenAI Admin API key listing was rate limited."
    else:
        status = "error"
        message = "OpenAI Admin API key listing failed."
    return OpenAIAdminKeyMonitorResult(
        status=status,
        confidence="unavailable",
        checked_at=normalize_monitor_timestamp(checked_at),
        message=message,
    )


def _record_from_admin_key(item: Mapping[str, Any]) -> OpenAIAdminKeyMonitorRecord | None:
    api_key_id = hashed_identifier("api_key_id", item.get("id"))
    if api_key_id is None:
        return None
    return OpenAIAdminKeyMonitorRecord(
        api_key_id=api_key_id,
        created_at=_optional_unix_timestamp(item.get("created_at"), "created_at"),
        last_used_at=_optional_unix_timestamp(item.get("last_used_at"), "last_used_at"),
    )


def _records_from_admin_key_items(
    items: list[Any],
) -> list[OpenAIAdminKeyMonitorRecord]:
    records: list[OpenAIAdminKeyMonitorRecord] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ContractError("OpenAI Admin API key list items must be objects")
        record = _record_from_admin_key(item)
        if record is None:
            raise ContractError("OpenAI Admin API key id is required")
        records.append(record)
    return records


def _optional_unix_timestamp(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"OpenAI Admin API key {field_name} must be a Unix timestamp")
    try:
        return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat().replace(
            "+00:00",
            "Z",
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise ContractError(f"OpenAI Admin API key {field_name} is invalid") from exc


def _optional_bool(value: Any, field_name: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ContractError(f"OpenAI Admin API keys {field_name} must be a boolean")
    return value
