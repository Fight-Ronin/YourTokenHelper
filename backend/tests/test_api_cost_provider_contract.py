import json

import pytest

from backend.core import API_COST_SOURCE_KINDS, ContractError
from backend.sources import (
    API_COST_PROVIDER_STATUSES,
    ApiCostProviderStatus,
    api_cost_provider_status_for,
    api_cost_provider_status_to_payload,
    api_cost_provider_statuses_for,
)


def test_api_cost_provider_statuses_preserve_multi_provider_allowlist() -> None:
    statuses = api_cost_provider_statuses_for(API_COST_SOURCE_KINDS)

    assert tuple(status.provider_id for status in statuses) == API_COST_SOURCE_KINDS
    assert statuses[0].provider_id == "openai_api_cost"
    assert statuses[0].status == "not_configured"
    assert statuses[0].adapter_verified is True
    assert {status.status for status in statuses[1:]} == {"needs_verified_adapter"}
    assert all(status.adapter_verified is False for status in statuses[1:])


def test_api_cost_provider_status_rejects_unknown_provider_without_echoing_input() -> None:
    secret_like_provider = "C:/Users/example/.openai/admin-key.txt"

    with pytest.raises(ContractError) as exc_info:
        api_cost_provider_status_for(secret_like_provider)

    assert str(exc_info.value) == "Unknown API cost provider"
    assert secret_like_provider not in str(exc_info.value)


def test_api_cost_provider_status_rejects_unknown_status() -> None:
    with pytest.raises(ContractError) as exc_info:
        ApiCostProviderStatus(
            provider_id="openai_api_cost",
            status="stored_but_assumed_ready",
            adapter_verified=True,
        )

    assert str(exc_info.value) == "Unknown API cost provider status"


def test_api_cost_provider_status_for_rejects_unknown_status_before_adapter_default() -> None:
    with pytest.raises(ContractError) as exc_info:
        api_cost_provider_status_for("claude_api_cost", status="stored_but_assumed_ready")

    assert str(exc_info.value) == "Unknown API cost provider status"


def test_unverified_provider_cannot_report_ready() -> None:
    with pytest.raises(ContractError) as exc_info:
        ApiCostProviderStatus(
            provider_id="claude_api_cost",
            status="ready",
            adapter_verified=False,
        )

    assert str(exc_info.value) == "Unverified API cost provider requires needs_verified_adapter"


def test_unverified_provider_status_for_rejects_concrete_status() -> None:
    with pytest.raises(ContractError) as exc_info:
        api_cost_provider_status_for(
            "claude_api_cost",
            credential_configured=True,
            status="permission_denied",
        )

    assert str(exc_info.value) == "Unverified API cost provider cannot accept concrete status"


def test_verified_provider_cannot_report_needs_verified_adapter() -> None:
    with pytest.raises(ContractError) as exc_info:
        ApiCostProviderStatus(
            provider_id="openai_api_cost",
            status="needs_verified_adapter",
            adapter_verified=True,
            credential_configured=False,
        )

    assert str(exc_info.value) == "Verified API cost provider cannot be needs_verified_adapter"


def test_verified_provider_cannot_report_ready_without_credential() -> None:
    with pytest.raises(ContractError) as exc_info:
        ApiCostProviderStatus(
            provider_id="openai_api_cost",
            status="ready",
            adapter_verified=True,
            credential_configured=False,
        )

    assert str(exc_info.value) == "API cost provider status requires a configured credential"


def test_api_cost_provider_status_payload_has_no_secret_or_path_fields() -> None:
    status = api_cost_provider_status_for("claude_api_cost", credential_configured=True)
    payload = api_cost_provider_status_to_payload(status)

    assert payload == {
        "provider_id": "claude_api_cost",
        "status": "needs_verified_adapter",
        "adapter_verified": False,
        "credential_configured": True,
        "message": "Provider billing adapter has not been verified.",
    }
    serialized = json.dumps(payload)
    assert "secret" not in serialized
    assert "C:/Users" not in serialized
    assert "admin-key" not in serialized


def test_verified_provider_with_credential_without_probe_is_unavailable() -> None:
    status = api_cost_provider_status_for("openai_api_cost", credential_configured=True)

    assert status.status == "unavailable"
    assert status.adapter_verified is True
    assert status.credential_configured is True


def test_verified_provider_can_report_explicit_permission_state() -> None:
    status = api_cost_provider_status_for(
        "openai_api_cost",
        credential_configured=True,
        status="permission_denied",
    )

    assert status.status == "permission_denied"
    assert status.status in API_COST_PROVIDER_STATUSES
