"""Live OpenAI Admin usage/cost fetching.

The returned payload is intentionally shaped like the existing sanitized
OpenAI Admin ingestion envelope. Endpoint failures retain only an HTTP status
code; response bodies are not surfaced.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib import error, parse, request

from backend.sources.refresh import rolling_7d_window_for_end_day


OPENAI_ADMIN_API_BASE_URL = "https://api.openai.com/v1"
OPENAI_ADMIN_USAGE_COMPLETIONS_PATH = "/organization/usage/completions"
OPENAI_ADMIN_COSTS_PATH = "/organization/costs"
OPENAI_ADMIN_ENDPOINT_MAX_PAGES = 20

OpenUrl = Callable[..., Any]


def fetch_openai_admin_usage_cost_payload(
    api_key: str,
    *,
    end_day_utc: str,
    api_base_url: str = OPENAI_ADMIN_API_BASE_URL,
    open_url: OpenUrl | None = None,
) -> dict[str, Any]:
    start_time, end_time = openai_admin_rolling_window_unix(end_day_utc)
    usage_params: dict[str, Any] = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": 31,
        "group_by": ["api_key_id", "project_id", "model"],
    }
    costs_params: dict[str, Any] = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": 31,
        "group_by": ["project_id", "line_item"],
    }
    return {
        "usage": fetch_paginated_openai_admin_endpoint(
            api_key,
            OPENAI_ADMIN_USAGE_COMPLETIONS_PATH,
            usage_params,
            api_base_url=api_base_url,
            open_url=open_url,
        ),
        "costs": fetch_paginated_openai_admin_endpoint(
            api_key,
            OPENAI_ADMIN_COSTS_PATH,
            costs_params,
            api_base_url=api_base_url,
            open_url=open_url,
        ),
    }


def fetch_paginated_openai_admin_endpoint(
    api_key: str,
    path: str,
    params: Mapping[str, Any],
    *,
    api_base_url: str = OPENAI_ADMIN_API_BASE_URL,
    timeout_seconds: float = 10.0,
    open_url: OpenUrl | None = None,
) -> dict[str, Any]:
    opener = open_url or request.urlopen
    page_params = dict(params)
    collected: list[Any] = []

    for _ in range(OPENAI_ADMIN_ENDPOINT_MAX_PAGES):
        payload = _request_openai_admin_json(
            api_key,
            path,
            page_params,
            api_base_url=api_base_url,
            timeout_seconds=timeout_seconds,
            open_url=opener,
        )
        if "error" in payload:
            return _endpoint_error_payload(payload["error"]["status"], data=collected)

        data = payload.get("data")
        if not isinstance(data, list):
            return _endpoint_error_payload(None, data=collected)
        collected.extend(data)

        has_more = payload.get("has_more") is True
        next_page = payload.get("next_page")
        if not has_more:
            response = dict(payload)
            response["data"] = collected
            return response
        if not isinstance(next_page, str) or not next_page.strip():
            return _endpoint_error_payload(None, data=collected)
        page_params["page"] = next_page.strip()

    return _endpoint_error_payload(None, data=collected)


def openai_admin_rolling_window_unix(end_day_utc: str) -> tuple[int, int]:
    window_start, window_end = rolling_7d_window_for_end_day(end_day_utc)
    start_day = dt.date.fromisoformat(window_start)
    end_day = dt.date.fromisoformat(window_end) + dt.timedelta(days=1)
    start_at = dt.datetime.combine(start_day, dt.time(), tzinfo=dt.timezone.utc)
    end_at = dt.datetime.combine(end_day, dt.time(), tzinfo=dt.timezone.utc)
    return int(start_at.timestamp()), int(end_at.timestamp())


def _request_openai_admin_json(
    api_key: str,
    path: str,
    params: Mapping[str, Any],
    *,
    api_base_url: str,
    timeout_seconds: float,
    open_url: OpenUrl,
) -> dict[str, Any]:
    http_request = request.Request(
        _openai_admin_url(api_base_url, path, params),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key.strip()}",
        },
        method="GET",
    )
    try:
        with open_url(http_request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None)
            if isinstance(status, int) and status >= 400:
                return _endpoint_error_payload(status)
            body = response.read(4_194_304)
    except error.HTTPError as exc:
        return _endpoint_error_payload(exc.code)
    except (OSError, TimeoutError, error.URLError):
        return _endpoint_error_payload(None)

    try:
        parsed = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _endpoint_error_payload(None)
    if not isinstance(parsed, Mapping):
        return _endpoint_error_payload(None)
    return dict(parsed)


def _openai_admin_url(
    api_base_url: str,
    path: str,
    params: Mapping[str, Any],
) -> str:
    base = api_base_url.rstrip("/")
    query = parse.urlencode(params, doseq=True)
    return f"{base}{path}?{query}"


def _endpoint_error_payload(
    status_code: int | None,
    *,
    data: list[Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"status": status_code}}
    if data:
        payload["data"] = data
    return payload
