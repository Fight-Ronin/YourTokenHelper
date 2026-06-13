#!/usr/bin/env python3
"""Probe OpenAI organization usage/cost data and emit a redacted summary."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE_URL = "https://api.openai.com/v1"
USAGE_PATH = "/organization/usage/completions"
COSTS_PATH = "/organization/costs"
ID_KEYS = {
    "api_key_id",
    "project_id",
    "user_id",
    "organization_id",
    "request_id",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe OpenAI organization usage/cost APIs without exposing secrets."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Fetch live data from OpenAI.")
    mode.add_argument(
        "--fixture",
        default=None,
        help="Read a fixture JSON payload instead of making network requests.",
    )
    parser.add_argument("--days", type=int, default=7, help="Number of UTC days to inspect.")
    parser.add_argument("--start-date", help="Inclusive UTC date, YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Exclusive UTC date, YYYY-MM-DD.")
    parser.add_argument(
        "--output",
        help="Write redacted summary JSON to this path. Defaults to stdout.",
    )
    parser.add_argument(
        "--api-base-url",
        default=API_BASE_URL,
        help="Override API base URL for testing.",
    )
    return parser.parse_args()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def require_api_key() -> tuple[str, str]:
    load_dotenv(Path(".env.local"))
    load_dotenv(Path(".env"))
    if os.environ.get("OPENAI_ADMIN_KEY"):
        return os.environ["OPENAI_ADMIN_KEY"], "OPENAI_ADMIN_KEY"
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], "OPENAI_API_KEY"
    raise SystemExit(
        "No OPENAI_ADMIN_KEY or OPENAI_API_KEY found in the environment or local .env files."
    )


def utc_window(args: argparse.Namespace) -> tuple[int, int]:
    if args.start_date or args.end_date:
        if not args.start_date or not args.end_date:
            raise SystemExit("--start-date and --end-date must be provided together.")
        start = parse_utc_date(args.start_date)
        end = parse_utc_date(args.end_date)
    else:
        today = dt.datetime.now(dt.timezone.utc).date()
        end = dt.datetime.combine(today + dt.timedelta(days=1), dt.time.min, dt.timezone.utc)
        start = end - dt.timedelta(days=args.days)
    if end <= start:
        raise SystemExit("End date must be after start date.")
    return int(start.timestamp()), int(end.timestamp())


def parse_utc_date(value: str) -> dt.datetime:
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid date {value!r}; expected YYYY-MM-DD.") from exc
    return dt.datetime.combine(parsed, dt.time.min, dt.timezone.utc)


def request_json(
    api_base_url: str,
    api_key: str,
    path: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{api_base_url.rstrip('/')}{path}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "error": {
                "status": exc.code,
                "reason": exc.reason,
                "body": safe_parse_json(body),
            }
        }
    except urllib.error.URLError as exc:
        return {"error": {"reason": str(exc.reason)}}


def safe_parse_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value[:500]


def live_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    api_key, key_source = require_api_key()
    start_time, end_time = utc_window(args)
    common_params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": 31,
    }
    usage_params = {
        **common_params,
        "group_by": ["api_key_id", "project_id", "model"],
    }
    costs_params = {
        **common_params,
        "group_by": ["project_id", "line_item"],
    }
    payload = {
        "usage": request_json(args.api_base_url, api_key, USAGE_PATH, usage_params),
        "costs": request_json(args.api_base_url, api_key, COSTS_PATH, costs_params),
        "allowance": {
            "status": "not_probed_no_official_endpoint_configured",
            "source": "probe",
            "reason": "The spike intentionally avoids private billing/dashboard endpoints.",
        },
    }
    metadata = {
        "mode": "live",
        "key_source": key_source,
        "window": {"start_time": start_time, "end_time": end_time},
    }
    return payload, metadata


def fixture_payload(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    start_times = [
        item.get("start_time")
        for item in payload.get("usage", {}).get("data", [])
        if isinstance(item.get("start_time"), int)
    ]
    end_times = [
        item.get("end_time")
        for item in payload.get("usage", {}).get("data", [])
        if isinstance(item.get("end_time"), int)
    ]
    metadata = {
        "mode": "fixture",
        "fixture": str(path),
        "window": {
            "start_time": min(start_times) if start_times else None,
            "end_time": max(end_times) if end_times else None,
        },
    }
    return payload, metadata


def summarize(payload: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage", {})
    costs = payload.get("costs", {})
    daily = summarize_daily(usage, costs)
    rolling = summarize_rolling(daily)
    return redact_ids(
        {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "mode": metadata.get("mode"),
            "source": {
                "key_source": metadata.get("key_source"),
                "fixture": metadata.get("fixture"),
            },
            "window": metadata.get("window"),
            "source_states": {
                "usage": source_state(usage),
                "costs": source_state(costs),
                "allowance": payload.get("allowance")
                or {
                    "status": "unavailable",
                    "source": "probe",
                    "reason": "No allowance data was present.",
                },
            },
            "daily": daily,
            "rolling_7d": rolling,
            "notes": [
                "Cost is secondary context and may lag or be unavailable.",
                "Allowance/remaining/reset must stay explicitly labeled by source.",
            ],
        }
    )


def source_state(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        status = error.get("status")
        if status in (401, 403):
            state = "permission_denied"
        else:
            state = "error"
        return {"status": state, "error": redact_ids(error)}
    if isinstance(payload, dict) and payload.get("data"):
        return {"status": "available", "bucket_count": len(payload["data"])}
    if isinstance(payload, dict):
        return {"status": "no_data"}
    return {"status": "unavailable"}


def summarize_daily(usage: dict[str, Any], costs: dict[str, Any]) -> list[dict[str, Any]]:
    by_day: dict[int, dict[str, Any]] = {}
    for bucket in usage.get("data", []) if isinstance(usage, dict) else []:
        if not isinstance(bucket, dict):
            continue
        day = ensure_day(by_day, bucket)
        for result in bucket.get("results", []) or []:
            if not isinstance(result, dict):
                continue
            day["input_tokens"] += int(result.get("input_tokens") or 0)
            day["output_tokens"] += int(result.get("output_tokens") or 0)
            day["cached_input_tokens"] += int(result.get("input_cached_tokens") or 0)
            day["requests"] += int(result.get("num_model_requests") or 0)
            add_breakdown(day["by_model"], result.get("model"), result)
            add_breakdown(day["by_api_key"], result.get("api_key_id"), result, "api_key")
            add_breakdown(day["by_project"], result.get("project_id"), result, "project")

    for bucket in costs.get("data", []) if isinstance(costs, dict) else []:
        if not isinstance(bucket, dict):
            continue
        day = ensure_day(by_day, bucket)
        for result in bucket.get("results", []) or []:
            if not isinstance(result, dict):
                continue
            amount = result.get("amount") or {}
            if isinstance(amount, dict) and str(amount.get("currency", "")).lower() == "usd":
                day["cost_usd"] += float(amount.get("value") or 0)

    for day in by_day.values():
        day["total_tokens"] = day["input_tokens"] + day["output_tokens"]
        day["cost_usd"] = round(day["cost_usd"], 6)
    return [by_day[key] for key in sorted(by_day)]


def ensure_day(by_day: dict[int, dict[str, Any]], bucket: dict[str, Any]) -> dict[str, Any]:
    start_time = int(bucket.get("start_time") or 0)
    end_time = int(bucket.get("end_time") or 0)
    if start_time not in by_day:
        by_day[start_time] = {
            "start_time": start_time,
            "end_time": end_time,
            "date_utc": dt.datetime.fromtimestamp(start_time, dt.timezone.utc)
            .date()
            .isoformat(),
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "cost_usd": 0.0,
            "by_model": {},
            "by_api_key": {},
            "by_project": {},
        }
    return by_day[start_time]


def add_breakdown(
    target: dict[str, Any],
    key: Any,
    result: dict[str, Any],
    redact_kind: str | None = None,
) -> None:
    if key and redact_kind:
        label = hash_id(redact_kind, str(key))
    else:
        label = str(key) if key else "ungrouped"
    if label not in target:
        target[label] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "requests": 0,
        }
    target[label]["input_tokens"] += int(result.get("input_tokens") or 0)
    target[label]["output_tokens"] += int(result.get("output_tokens") or 0)
    target[label]["cached_input_tokens"] += int(result.get("input_cached_tokens") or 0)
    target[label]["requests"] += int(result.get("num_model_requests") or 0)


def summarize_rolling(daily: list[dict[str, Any]]) -> dict[str, Any]:
    last_days = daily[-7:]
    return {
        "days": len(last_days),
        "input_tokens": sum(day["input_tokens"] for day in last_days),
        "output_tokens": sum(day["output_tokens"] for day in last_days),
        "cached_input_tokens": sum(day["cached_input_tokens"] for day in last_days),
        "total_tokens": sum(day["total_tokens"] for day in last_days),
        "requests": sum(day["requests"] for day in last_days),
        "cost_usd": round(sum(day["cost_usd"] for day in last_days), 6),
        "allowance": {
            "status": "not_calculated",
            "reason": "A configured or official allowance window is required.",
        },
    }


def redact_ids(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_ids(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in ID_KEYS and isinstance(item, str):
                redacted[key] = hash_id(key, item)
            else:
                redacted[key] = redact_ids(item)
        return redacted
    return value


def hash_id(kind: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    prefix = kind.removesuffix("_id").replace("_", "-")
    return f"{prefix}_{digest}"


def write_output(summary: dict[str, Any], output: str | None) -> None:
    encoded = json.dumps(summary, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
        print(f"Wrote redacted summary to {path}")
    else:
        print(encoded)


def main() -> None:
    args = parse_args()
    fixture = args.fixture
    if not args.live and fixture is None:
        fixture = "experiments/fixtures/openai/sample_probe_response.json"
    if args.live:
        payload, metadata = live_payload(args)
    else:
        payload, metadata = fixture_payload(Path(fixture))
    write_output(summarize(payload, metadata), args.output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
