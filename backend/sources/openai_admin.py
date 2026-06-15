"""OpenAI Admin Usage/Costs payload ingestion for the API cost source."""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping

from backend.core import ContractError, UsageEvent
from backend.sources.base import SourceState
from backend.sources.refresh import rolling_7d_window_for_end_day
from backend.storage import (
    CostBucketRecord,
    record_sync_run,
    replace_cost_records_for_source_window,
    replace_usage_events_for_source_window,
    upsert_source,
)


OPENAI_API_COST_SOURCE_KIND = "openai_api_cost"
OPENAI_ADMIN_SOURCE_ID = "openai_api_cost:admin_api"


@dataclass(frozen=True)
class OpenAIAdminSyncResult:
    state: SourceState
    usage_events_seen: int
    cost_records_seen: int
    sync_run_id: int


def openai_admin_usage_events_from_payload(
    payload: Mapping[str, Any],
    *,
    source_id: str = OPENAI_ADMIN_SOURCE_ID,
) -> list[UsageEvent]:
    usage = payload.get("usage")
    events: list[UsageEvent] = []
    for bucket in bucket_items(usage):
        started_at = timestamp_from_bucket(bucket)
        if started_at is None:
            continue
        for result in result_items(bucket):
            input_tokens = int_value(result.get("input_tokens")) or 0
            output_tokens = int_value(result.get("output_tokens")) or 0
            total_tokens = input_tokens + output_tokens
            if total_tokens <= 0:
                continue
            request_count = int_value(result.get("num_model_requests"))
            if request_count is None:
                request_count = 1
            events.append(
                UsageEvent(
                    source_kind=OPENAI_API_COST_SOURCE_KIND,
                    source_id=source_id,
                    started_at=started_at,
                    model=string_value(result.get("model")),
                    project_id=hashed_identifier("project_id", result.get("project_id")),
                    api_key_id=hashed_identifier("api_key_id", result.get("api_key_id")),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=first_int_value(
                        result,
                        "input_cached_tokens",
                        "cached_input_tokens",
                    ),
                    reasoning_output_tokens=first_int_value(
                        result,
                        "output_reasoning_tokens",
                        "reasoning_output_tokens",
                    ),
                    total_tokens=total_tokens,
                    request_count=request_count,
                    confidence="official",
                )
            )
    return events


def openai_admin_cost_records_from_payload(
    payload: Mapping[str, Any],
    *,
    source_id: str = OPENAI_ADMIN_SOURCE_ID,
) -> list[CostBucketRecord]:
    costs = payload.get("costs")
    records: list[CostBucketRecord] = []
    for bucket in bucket_items(costs):
        day_utc = day_from_bucket(bucket)
        if day_utc is None:
            continue
        for result in result_items(bucket):
            amount = result.get("amount")
            if not isinstance(amount, Mapping):
                continue
            currency = string_value(amount.get("currency"))
            if currency is None or currency.lower() != "usd":
                continue
            cost_usd = float_value(amount.get("value"))
            if cost_usd is None:
                continue
            records.append(
                CostBucketRecord(
                    day_utc=day_utc,
                    source_kind=OPENAI_API_COST_SOURCE_KIND,
                    source_id=source_id,
                    project_id=hashed_identifier("project_id", result.get("project_id")),
                    api_key_id=hashed_identifier("api_key_id", result.get("api_key_id")),
                    cost_usd=cost_usd,
                    currency="USD",
                )
            )
    return records


def sync_openai_admin_usage_cost_payload(
    connection: sqlite3.Connection,
    payload: Mapping[str, Any],
    *,
    end_day_utc: str,
    started_at: str,
    source_id: str = OPENAI_ADMIN_SOURCE_ID,
) -> OpenAIAdminSyncResult:
    window_start, window_end = rolling_7d_window_for_end_day(end_day_utc)
    state = source_state_from_payload(payload, source_id=source_id)
    usage_events = [
        event
        for event in openai_admin_usage_events_from_payload(payload, source_id=source_id)
        if window_start <= event.day_utc <= window_end
    ]
    cost_records = [
        record
        for record in openai_admin_cost_records_from_payload(payload, source_id=source_id)
        if window_start <= record.day_utc <= window_end
    ]

    upsert_source(
        connection,
        source_kind=state.source_kind,
        source_id=state.source_id,
        status=state.status,
        confidence=state.confidence,
    )
    if state.status == "ready":
        replace_usage_events_for_source_window(
            connection,
            source_kind=state.source_kind,
            source_id=state.source_id,
            start_day_utc=window_start,
            end_day_utc=window_end,
            events=usage_events,
        )
        replace_cost_records_for_source_window(
            connection,
            source_kind=state.source_kind,
            source_id=state.source_id,
            start_day_utc=window_start,
            end_day_utc=window_end,
            records=cost_records,
        )

    sync_run_id = record_sync_run(
        connection,
        source_kind=state.source_kind,
        source_id=state.source_id,
        status=state.status,
        started_at=started_at,
        events_seen=len(usage_events) + len(cost_records),
        message=state.message,
    )
    return OpenAIAdminSyncResult(
        state=state,
        usage_events_seen=len(usage_events),
        cost_records_seen=len(cost_records),
        sync_run_id=sync_run_id,
    )


def source_state_from_payload(
    payload: Mapping[str, Any],
    *,
    source_id: str,
) -> SourceState:
    validate_openai_admin_payload_envelope(payload)
    usage = payload.get("usage")
    costs = payload.get("costs")
    usage_has_data = bool(bucket_items(usage))
    costs_has_data = bool(bucket_items(costs))
    if usage_has_data or costs_has_data:
        message = (
            "OpenAI Admin usage or costs payload is partially available."
            if has_error(usage) or has_error(costs)
            else "OpenAI Admin usage and costs payload is available."
        )
        return SourceState(
            source_kind=OPENAI_API_COST_SOURCE_KIND,
            source_id=source_id,
            status="ready",
            confidence="official",
            message=message,
        )
    if has_permission_error(usage) or has_permission_error(costs):
        return SourceState(
            source_kind=OPENAI_API_COST_SOURCE_KIND,
            source_id=source_id,
            status="permission_denied",
            confidence="unavailable",
            message="OpenAI Admin usage or costs access was denied.",
        )
    if has_error(usage) or has_error(costs):
        return SourceState(
            source_kind=OPENAI_API_COST_SOURCE_KIND,
            source_id=source_id,
            status="error",
            confidence="unavailable",
            message="OpenAI Admin usage or costs sync failed.",
        )
    return SourceState(
        source_kind=OPENAI_API_COST_SOURCE_KIND,
        source_id=source_id,
        status="ready",
        confidence="official",
        message="OpenAI Admin usage and costs payload has no rows.",
    )


def validate_openai_admin_payload_envelope(payload: Mapping[str, Any]) -> None:
    for endpoint_name in ("usage", "costs"):
        endpoint = payload.get(endpoint_name)
        if not isinstance(endpoint, Mapping):
            raise ContractError(
                f"OpenAI Admin {endpoint_name} endpoint payload is required"
            )
        has_data = isinstance(endpoint.get("data"), list)
        has_error = isinstance(endpoint.get("error"), Mapping)
        if not has_data and not has_error:
            raise ContractError(
                f"OpenAI Admin {endpoint_name} endpoint payload must include data or error"
            )


def bucket_items(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, Mapping)]


def result_items(bucket: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    results = bucket.get("results")
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, Mapping)]


def timestamp_from_bucket(bucket: Mapping[str, Any]) -> str | None:
    start_time = int_value(bucket.get("start_time"))
    if start_time is None:
        return None
    try:
        return (
            dt.datetime.fromtimestamp(start_time, dt.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise ContractError("OpenAI Admin bucket start_time is invalid") from exc


def day_from_bucket(bucket: Mapping[str, Any]) -> str | None:
    timestamp = timestamp_from_bucket(bucket)
    return timestamp[:10] if timestamp is not None else None


def hashed_identifier(kind: str, value: Any) -> str | None:
    text = string_value(value)
    if text is None:
        return None
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    prefix = kind.removesuffix("_id").replace("_", "-")
    return f"{prefix}_{digest}"


def has_permission_error(payload: Any) -> bool:
    if not isinstance(payload, Mapping):
        return False
    error = payload.get("error")
    return isinstance(error, Mapping) and error.get("status") in {401, 403}


def has_error(payload: Any) -> bool:
    return isinstance(payload, Mapping) and isinstance(payload.get("error"), Mapping)


def first_int_value(record: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = int_value(record.get(key))
        if value is not None:
            return value
    return None


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def float_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def string_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
