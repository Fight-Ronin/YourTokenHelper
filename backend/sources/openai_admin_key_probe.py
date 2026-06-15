"""Env-key live probe for the OpenAI Admin API key monitor."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib import error, request

from backend.sources.openai_admin_key_monitor import (
    OpenAIAdminKeyMonitorResult,
    openai_admin_key_monitor_from_payload,
)


OPENAI_ADMIN_KEY_ENV_VAR = "OPENAI_ADMIN_KEY"
OPENAI_ADMIN_API_KEYS_LIST_URL = (
    "https://api.openai.com/v1/organization/admin_api_keys?limit=1"
)

FetchAdminApiKeysPayload = Callable[[str], Mapping[str, Any]]
OpenUrl = Callable[..., Any]


def probe_openai_admin_api_key(
    api_key: str,
    *,
    checked_at: str,
    fetch_admin_api_keys: FetchAdminApiKeysPayload | None = None,
) -> OpenAIAdminKeyMonitorResult:
    fetcher = fetch_admin_api_keys or fetch_openai_admin_api_keys_payload
    return openai_admin_key_monitor_from_payload(
        fetcher(api_key),
        checked_at=checked_at,
    )


def fetch_openai_admin_api_keys_payload(
    api_key: str,
    *,
    timeout_seconds: float = 10.0,
    open_url: OpenUrl | None = None,
) -> dict[str, Any]:
    opener = open_url or request.urlopen
    http_request = request.Request(
        OPENAI_ADMIN_API_KEYS_LIST_URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key.strip()}",
        },
        method="GET",
    )

    try:
        with opener(http_request, timeout=timeout_seconds) as response:
            body = response.read(1_048_576)
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
    return {"admin_api_keys": dict(parsed)}


def _endpoint_error_payload(status_code: int | None) -> dict[str, Any]:
    return {"admin_api_keys": {"error": {"status": status_code}}}
