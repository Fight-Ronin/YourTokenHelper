"""Stable core usage contracts for backend and UI layers."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


SOURCE_KINDS = (
    "codex",
    "claude_code",
    "cursor",
    "gemini_cli",
    "github_copilot",
    "openai_api_cost",
)
CONFIDENCE_VALUES = ("official", "local_exact", "local_estimated", "manual", "unavailable")


class ContractError(ValueError):
    """Raised when a usage contract object is invalid."""


@dataclass(frozen=True)
class TokenTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        for field_name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("cached_input_tokens", self.cached_input_tokens),
            ("reasoning_output_tokens", self.reasoning_output_tokens),
            ("total_tokens", self.total_tokens),
        ):
            validate_non_negative_int(field_name, value)


@dataclass(frozen=True)
class UsageEvent:
    source_kind: str
    source_id: str
    started_at: str
    total_tokens: int
    confidence: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    cost_usd: float | None = None
    usage_credits: float | None = None
    session_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    api_key_id: str | None = None
    raw_source_ref: str | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in SOURCE_KINDS:
            raise ContractError(f"Unknown source_kind: {self.source_kind}")
        if not self.source_id.strip():
            raise ContractError("source_id is required")
        if self.confidence not in CONFIDENCE_VALUES:
            raise ContractError(f"Unknown confidence: {self.confidence}")

        object.__setattr__(self, "started_at", normalize_utc_timestamp(self.started_at))
        validate_non_negative_int("total_tokens", self.total_tokens)
        for field_name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("cached_input_tokens", self.cached_input_tokens),
            ("reasoning_output_tokens", self.reasoning_output_tokens),
        ):
            if value is not None:
                validate_non_negative_int(field_name, value)
        if self.cost_usd is not None and self.cost_usd < 0:
            raise ContractError("cost_usd must be non-negative")
        if self.usage_credits is not None and self.usage_credits < 0:
            raise ContractError("usage_credits must be non-negative")

    @property
    def day_utc(self) -> str:
        return self.started_at[:10]

    def token_totals(self) -> TokenTotals:
        return TokenTotals(
            input_tokens=self.input_tokens or 0,
            output_tokens=self.output_tokens or 0,
            cached_input_tokens=self.cached_input_tokens or 0,
            reasoning_output_tokens=self.reasoning_output_tokens or 0,
            total_tokens=self.total_tokens,
        )


def normalize_utc_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        raise ContractError("started_at is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"started_at must be ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def validate_non_negative_int(field_name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{field_name} must be an integer")
    if value < 0:
        raise ContractError(f"{field_name} must be non-negative")
