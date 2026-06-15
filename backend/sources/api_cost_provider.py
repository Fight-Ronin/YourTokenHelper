"""API cost provider status contract.

This module tracks whether a provider adapter is safe to use. It does not store
or inspect credentials, and it never reports a provider as ready without an
explicit status from a verified adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.core import API_COST_SOURCE_KINDS, ContractError


API_COST_PROVIDER_STATUSES = (
    "not_configured",
    "needs_verified_adapter",
    "ready",
    "invalid_key",
    "permission_denied",
    "rate_limited",
    "unavailable",
)
CONFIGURED_CREDENTIAL_STATUSES = (
    "ready",
    "invalid_key",
    "permission_denied",
    "rate_limited",
    "unavailable",
)
VERIFIED_API_COST_PROVIDER_IDS = ("openai_api_cost",)


@dataclass(frozen=True)
class ApiCostProviderStatus:
    provider_id: str
    status: str
    adapter_verified: bool = False
    credential_configured: bool = False
    message: str | None = None

    def __post_init__(self) -> None:
        validate_api_cost_provider_id(self.provider_id)
        _validate_api_cost_provider_status(self.status)
        if self.adapter_verified and self.status == "needs_verified_adapter":
            raise ContractError("Verified API cost provider cannot be needs_verified_adapter")
        if not self.adapter_verified and self.status != "needs_verified_adapter":
            raise ContractError("Unverified API cost provider requires needs_verified_adapter")
        if self.status == "not_configured" and self.credential_configured:
            raise ContractError("Configured API cost provider cannot be not_configured")
        if self.status in CONFIGURED_CREDENTIAL_STATUSES and not self.credential_configured:
            raise ContractError("API cost provider status requires a configured credential")


def validate_api_cost_provider_id(provider_id: str) -> None:
    if provider_id not in API_COST_SOURCE_KINDS:
        raise ContractError("Unknown API cost provider")


def _validate_api_cost_provider_status(status: str) -> None:
    if status not in API_COST_PROVIDER_STATUSES:
        raise ContractError("Unknown API cost provider status")


def api_cost_provider_status_for(
    provider_id: str,
    *,
    credential_configured: bool = False,
    status: str | None = None,
    verified_provider_ids: Iterable[str] = VERIFIED_API_COST_PROVIDER_IDS,
) -> ApiCostProviderStatus:
    validate_api_cost_provider_id(provider_id)
    if status is not None:
        _validate_api_cost_provider_status(status)
    verified_ids = _validated_provider_set(verified_provider_ids)
    adapter_verified = provider_id in verified_ids

    if not adapter_verified:
        if status not in (None, "needs_verified_adapter"):
            raise ContractError("Unverified API cost provider cannot accept concrete status")
        return ApiCostProviderStatus(
            provider_id=provider_id,
            status="needs_verified_adapter",
            adapter_verified=False,
            credential_configured=credential_configured,
            message="Provider billing adapter has not been verified.",
        )

    if status is not None:
        return ApiCostProviderStatus(
            provider_id=provider_id,
            status=status,
            adapter_verified=True,
            credential_configured=credential_configured,
        )

    if not credential_configured:
        return ApiCostProviderStatus(
            provider_id=provider_id,
            status="not_configured",
            adapter_verified=True,
            credential_configured=False,
        )

    return ApiCostProviderStatus(
        provider_id=provider_id,
        status="unavailable",
        adapter_verified=True,
        credential_configured=True,
        message="Provider credential has not been validated.",
    )


def api_cost_provider_statuses_for(
    provider_ids: Iterable[str] = API_COST_SOURCE_KINDS,
    *,
    credential_provider_ids: Iterable[str] = (),
    verified_provider_ids: Iterable[str] = VERIFIED_API_COST_PROVIDER_IDS,
) -> tuple[ApiCostProviderStatus, ...]:
    credential_ids = _validated_provider_set(credential_provider_ids)
    return tuple(
        api_cost_provider_status_for(
            provider_id,
            credential_configured=provider_id in credential_ids,
            verified_provider_ids=verified_provider_ids,
        )
        for provider_id in provider_ids
    )


def api_cost_provider_status_to_payload(status: ApiCostProviderStatus) -> dict[str, object]:
    payload: dict[str, object] = {
        "provider_id": status.provider_id,
        "status": status.status,
        "adapter_verified": status.adapter_verified,
        "credential_configured": status.credential_configured,
    }
    if status.message:
        payload["message"] = status.message
    return payload


def _validated_provider_set(provider_ids: Iterable[str]) -> set[str]:
    validated_ids: set[str] = set()
    for provider_id in provider_ids:
        validate_api_cost_provider_id(provider_id)
        validated_ids.add(provider_id)
    return validated_ids
