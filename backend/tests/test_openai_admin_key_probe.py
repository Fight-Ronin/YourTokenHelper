import io
import json
from pathlib import Path
from urllib import error

from backend.sources import (
    OPENAI_ADMIN_API_KEYS_LIST_URL,
    OPENAI_ADMIN_KEY_ENV_VAR,
    fetch_openai_admin_api_keys_payload,
    probe_openai_admin_api_key,
)


FIXTURE_PATH = Path("experiments/fixtures/openai/sample_admin_api_keys_response.json")


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self.body[:size]


def fixture_payload():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_probe_openai_admin_api_key_reuses_redacted_monitor_parser():
    result = probe_openai_admin_api_key(
        "sk-admin-fixture-secret",
        checked_at="2026-06-15T00:00:00Z",
        fetch_admin_api_keys=lambda _api_key: fixture_payload(),
    )

    assert result.status == "ready"
    assert result.confidence == "official"
    assert result.key_count == 2
    assert result.keys[0].api_key_id.startswith("api-key_")


def test_fetch_openai_admin_api_keys_payload_wraps_json_response():
    captured = {}

    def fake_open_url(http_request, *, timeout):
        captured["url"] = http_request.full_url
        captured["authorization"] = http_request.headers["Authorization"]
        captured["timeout"] = timeout
        return FakeResponse(b'{"data":[{"id":"key_fixture_admin"}],"has_more":false}')

    payload = fetch_openai_admin_api_keys_payload(
        " sk-admin-fixture-secret ",
        timeout_seconds=3.0,
        open_url=fake_open_url,
    )

    assert captured == {
        "url": OPENAI_ADMIN_API_KEYS_LIST_URL,
        "authorization": "Bearer sk-admin-fixture-secret",
        "timeout": 3.0,
    }
    assert payload == {
        "admin_api_keys": {
            "data": [{"id": "key_fixture_admin"}],
            "has_more": False,
        }
    }


def test_fetch_openai_admin_api_keys_payload_maps_http_error_status_only():
    def fake_open_url(_http_request, *, timeout):
        raise error.HTTPError(
            OPENAI_ADMIN_API_KEYS_LIST_URL,
            403,
            "Forbidden",
            {},
            io.BytesIO(b'{"error":{"message":"fixture secret detail"}}'),
        )

    payload = fetch_openai_admin_api_keys_payload(
        "sk-personal-fixture-secret",
        open_url=fake_open_url,
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {"admin_api_keys": {"error": {"status": 403}}}
    assert "fixture secret detail" not in text
    assert "sk-personal-fixture-secret" not in text


def test_openai_admin_key_env_var_is_separate_from_personal_key_name():
    assert OPENAI_ADMIN_KEY_ENV_VAR == "OPENAI_ADMIN_KEY"
