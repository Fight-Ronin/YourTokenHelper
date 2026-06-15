import json
from pathlib import Path

import pytest

from backend.core import ContractError
from backend.sources import (
    OPENAI_ADMIN_KEY_MONITOR_SOURCE_ID,
    openai_admin_key_monitor_from_payload,
    openai_admin_key_monitor_result_to_payload,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_admin_api_keys_response.json")


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_openai_admin_key_monitor_maps_list_response_without_raw_key_metadata():
    result = openai_admin_key_monitor_from_payload(
        fixture_payload(),
        checked_at="2026-06-15T00:00:00Z",
    )
    payload = openai_admin_key_monitor_result_to_payload(result)
    text = json.dumps(payload, sort_keys=True)

    assert result.source_id == OPENAI_ADMIN_KEY_MONITOR_SOURCE_ID
    assert result.status == "ready"
    assert result.confidence == "official"
    assert result.key_count == 2
    assert result.active_key_count == 1
    assert payload["keys"][0]["api_key_id"].startswith("api-key_")
    assert "key_fixture_admin" not in text
    assert "sk-admin" not in text
    assert "Main Admin Key" not in text
    assert "Usage Monitor Service Account" not in text


def test_openai_admin_key_monitor_maps_retrieve_response_without_raw_key_metadata():
    result = openai_admin_key_monitor_from_payload(
        {
            "admin_api_keys": {
                "object": "organization.admin_api_key",
                "id": "key_fixture_admin_single",
                "name": "Single Admin Key",
                "redacted_value": "sk-admin...single",
                "created_at": 1711471533,
                "last_used_at": 1711471534,
                "owner": {
                    "type": "service_account",
                    "id": "sa_fixture_owner",
                    "name": "Usage Monitor Service Account",
                },
            }
        },
        checked_at="2026-06-15T00:00:00Z",
    )
    payload = openai_admin_key_monitor_result_to_payload(result)
    text = json.dumps(payload, sort_keys=True)

    assert result.status == "ready"
    assert result.key_count == 1
    assert result.active_key_count == 1
    assert result.has_more is False
    assert payload["keys"][0]["api_key_id"].startswith("api-key_")
    assert "key_fixture_admin_single" not in text
    assert "sk-admin" not in text
    assert "Single Admin Key" not in text
    assert "Usage Monitor Service Account" not in text


@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [
        (401, "invalid_key"),
        (403, "permission_denied"),
        (429, "rate_limited"),
        (500, "error"),
    ],
)
def test_openai_admin_key_monitor_maps_explicit_endpoint_errors(
    status_code,
    expected_status,
):
    result = openai_admin_key_monitor_from_payload(
        {
            "admin_api_keys": {
                "error": {
                    "status": status_code,
                    "body": {"error": {"message": "fixture secret detail"}},
                }
            }
        },
        checked_at="2026-06-15T00:00:00Z",
    )
    payload = openai_admin_key_monitor_result_to_payload(result)
    text = json.dumps(payload, sort_keys=True)

    assert result.status == expected_status
    assert result.confidence == "unavailable"
    assert payload["keys"] == []
    assert "fixture secret detail" not in text


def test_openai_admin_key_monitor_rejects_missing_endpoint_envelope():
    with pytest.raises(
        ContractError,
        match="OpenAI Admin API keys endpoint payload is required",
    ):
        openai_admin_key_monitor_from_payload(
            {},
            checked_at="2026-06-15T00:00:00Z",
        )


def test_openai_admin_key_monitor_rejects_invalid_key_timestamp():
    payload = fixture_payload()
    payload["admin_api_keys"]["data"][0]["created_at"] = 999999999999999999999999

    with pytest.raises(
        ContractError,
        match="OpenAI Admin API key created_at is invalid",
    ):
        openai_admin_key_monitor_from_payload(
            payload,
            checked_at="2026-06-15T00:00:00Z",
        )


def test_openai_admin_key_monitor_rejects_invalid_has_more():
    payload = fixture_payload()
    payload["admin_api_keys"]["has_more"] = "false"

    with pytest.raises(
        ContractError,
        match="OpenAI Admin API keys has_more must be a boolean",
    ):
        openai_admin_key_monitor_from_payload(
            payload,
            checked_at="2026-06-15T00:00:00Z",
        )


def test_openai_admin_key_monitor_rejects_key_item_without_id():
    payload = fixture_payload()
    del payload["admin_api_keys"]["data"][0]["id"]

    with pytest.raises(
        ContractError,
        match="OpenAI Admin API key id is required",
    ):
        openai_admin_key_monitor_from_payload(
            payload,
            checked_at="2026-06-15T00:00:00Z",
        )
