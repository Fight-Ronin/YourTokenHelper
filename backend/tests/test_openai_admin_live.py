import json
from urllib import error, parse

from backend.sources.openai_admin_live import (
    OPENAI_ADMIN_COSTS_PATH,
    OPENAI_ADMIN_USAGE_COMPLETIONS_PATH,
    fetch_openai_admin_usage_cost_payload,
    fetch_paginated_openai_admin_endpoint,
    openai_admin_rolling_window_unix,
)


class FakeResponse:
    def __init__(self, payload: object, *, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit: int) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_openai_admin_rolling_window_unix_uses_exclusive_end_day():
    start_time, end_time = openai_admin_rolling_window_unix("2026-06-14")

    assert start_time == 1780876800
    assert end_time == 1781481600


def test_fetch_openai_admin_usage_cost_payload_builds_official_endpoint_requests():
    seen_urls: list[str] = []
    seen_authorization: list[str | None] = []

    def fake_open(request, *, timeout):
        del timeout
        seen_urls.append(request.full_url)
        seen_authorization.append(request.get_header("Authorization"))
        path = parse.urlparse(request.full_url).path
        query = parse.parse_qs(parse.urlparse(request.full_url).query)
        assert query["start_time"] == ["1780876800"]
        assert query["end_time"] == ["1781481600"]
        assert query["bucket_width"] == ["1d"]
        assert query["limit"] == ["31"]
        if path.endswith(OPENAI_ADMIN_USAGE_COMPLETIONS_PATH):
            assert query["group_by"] == ["api_key_id", "project_id", "model"]
            return FakeResponse({"data": [{"start_time": 1780876800, "results": []}]})
        assert path.endswith(OPENAI_ADMIN_COSTS_PATH)
        assert query["group_by"] == ["project_id", "line_item"]
        return FakeResponse({"data": [{"start_time": 1780876800, "results": []}]})

    payload = fetch_openai_admin_usage_cost_payload(
        " sk-admin-fixture-secret ",
        end_day_utc="2026-06-14",
        open_url=fake_open,
    )
    text = json.dumps(payload, sort_keys=True)

    assert len(seen_urls) == 2
    assert seen_authorization == [
        "Bearer sk-admin-fixture-secret",
        "Bearer sk-admin-fixture-secret",
    ]
    assert payload["usage"]["data"][0]["start_time"] == 1780876800
    assert payload["costs"]["data"][0]["start_time"] == 1780876800
    assert "sk-admin-fixture-secret" not in text


def test_fetch_paginated_openai_admin_endpoint_combines_pages():
    seen_pages: list[str | None] = []

    def fake_open(request, *, timeout):
        del timeout
        query = parse.parse_qs(parse.urlparse(request.full_url).query)
        seen_pages.append(query.get("page", [None])[0])
        if seen_pages[-1] is None:
            return FakeResponse(
                {
                    "data": [{"start_time": 1780876800, "results": []}],
                    "has_more": True,
                    "next_page": "cursor_fixture",
                }
            )
        return FakeResponse(
            {
                "data": [{"start_time": 1780963200, "results": []}],
                "has_more": False,
            }
        )

    payload = fetch_paginated_openai_admin_endpoint(
        "sk-admin-fixture-secret",
        OPENAI_ADMIN_USAGE_COMPLETIONS_PATH,
        {"start_time": 1780876800, "end_time": 1781481600},
        open_url=fake_open,
    )

    assert seen_pages == [None, "cursor_fixture"]
    assert [item["start_time"] for item in payload["data"]] == [1780876800, 1780963200]


def test_fetch_paginated_openai_admin_endpoint_redacts_http_error_body():
    def fake_open(request, *, timeout):
        del request, timeout
        raise error.HTTPError(
            url="https://api.openai.com/v1/organization/costs",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )

    payload = fetch_paginated_openai_admin_endpoint(
        "sk-admin-fixture-secret",
        OPENAI_ADMIN_COSTS_PATH,
        {"start_time": 1780876800, "end_time": 1781481600},
        open_url=fake_open,
    )
    text = json.dumps(payload, sort_keys=True)

    assert payload == {"error": {"status": 403}}
    assert "Forbidden" not in text
    assert "organization/costs" not in text
    assert "sk-admin-fixture-secret" not in text
