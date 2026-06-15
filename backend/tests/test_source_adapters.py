import sqlite3

import pytest

from backend.core import ContractError
from backend.sources import (
    ManualStatusAdapter,
    SourceState,
    sync_source_adapter,
)
from backend.storage import (
    initialize_schema,
    list_sources,
    query_daily_summary,
)


def memory_connection():
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_source_state_rejects_unknown_values():
    with pytest.raises(ContractError):
        SourceState(
            source_kind="unknown",
            source_id="unknown:mock",
            status="ready",
            confidence="local_exact",
        )

    with pytest.raises(ContractError):
        SourceState(
            source_kind="codex",
            source_id="codex:mock",
            status="secretly_ready",
            confidence="local_exact",
        )


def test_non_ready_manual_status_adapters_record_source_state_without_events():
    connection = memory_connection()
    adapters = [
        ManualStatusAdapter(
            source_kind="cursor",
            source_id="cursor:manual",
            status="not_found",
            confidence="local_estimated",
            message="Cursor local parser is not mature yet.",
        ),
        ManualStatusAdapter(
            source_kind="gemini_cli",
            source_id="gemini_cli:manual",
            status="setup_required",
            confidence="local_estimated",
            message="Gemini CLI needs telemetry or export setup.",
        ),
        ManualStatusAdapter(
            source_kind="github_copilot",
            source_id="github_copilot:manual",
            status="official_report",
            confidence="official",
            message="Use official or manual report import path.",
        ),
    ]

    for adapter in adapters:
        result = sync_source_adapter(
            connection,
            adapter,
            started_at="2026-06-14T00:00:00Z",
        )
        assert result.events_seen == 0

    summary = query_daily_summary(connection, "2026-06-14")
    sources = {
        item["source_kind"]: item
        for item in list_sources(connection)
    }

    assert summary.event_count == 0
    assert sources["cursor"]["status"] == "not_found"
    assert sources["gemini_cli"]["status"] == "setup_required"
    assert sources["github_copilot"]["status"] == "official_report"


def test_permission_error_records_recoverable_source_state_without_events():
    connection = memory_connection()

    result = sync_source_adapter(
        connection,
        FailingAdapter(PermissionError("denied")),
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")
    source = list_sources(connection)[0]

    assert result.state.status == "permission_denied"
    assert result.events_seen == 0
    assert source["status"] == "permission_denied"
    assert source["confidence"] == "unavailable"
    assert summary.event_count == 0


def test_contract_error_records_recoverable_error_without_events():
    connection = memory_connection()

    result = sync_source_adapter(
        connection,
        FailingAdapter(ContractError("bad aggregate record")),
        started_at="2026-06-14T00:00:00Z",
    )
    summary = query_daily_summary(connection, "2026-06-14")
    source = list_sources(connection)[0]

    assert result.state.status == "error"
    assert result.events_seen == 0
    assert source["status"] == "error"
    assert source["confidence"] == "unavailable"
    assert summary.event_count == 0


class FailingAdapter:
    source_kind = "codex"
    source_id = "codex:failing"

    def __init__(self, failure):
        self.failure = failure

    def get_state(self):
        return SourceState(
            source_kind=self.source_kind,
            source_id=self.source_id,
            status="ready",
            confidence="local_exact",
        )

    def read_events(self):
        raise self.failure
